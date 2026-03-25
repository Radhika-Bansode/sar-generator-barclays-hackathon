import os
import logging
from typing import Dict, Any, Optional
from src.processors.transaction_processor import TransactionProcessor
from src.processors.risk_analyzer import RiskAnalyzer
from src.generators.rag_engine import RAGEngine
from src.generators.narrative_generator_template import TemplateNarrativeGenerator
from src.generators.audit_tracker import AuditTrailGenerator
from database.operations import (
    create_case,
    update_case_risk,
    update_case_metrics,
    add_transactions_bulk,
    save_narrative,
    save_audit_log,
    get_case_by_id
)

logger = logging.getLogger(__name__)

class SARPipeline:
    def __init__(self, llama_generator=None):
        self.transaction_processor = TransactionProcessor()
        self.risk_analyzer = RiskAnalyzer()
        self.rag_engine = RAGEngine()
        self.template_generator = TemplateNarrativeGenerator(rag_engine=self.rag_engine)
        self.audit_tracker = AuditTrailGenerator()
        
        # Determine which generator to use
        # Fallback to template if llama_generator is not provided
        self.primary_generator = llama_generator if llama_generator else self.template_generator
        self.generator_name = "llama" if llama_generator else "template"

    def process_case(self, csv_path: str, customer_info: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the complete E2E pipeline for SAR generation."""
        try:
            logger.info("Starting SAR Pipeline...")
            
            # Step 1: Process Transactions
            logger.info("Processing Transactions...")
            case_data_processed = self.transaction_processor.process_csv(csv_path, customer_info)
            case_id = case_data_processed.get('case_id')
            tx_metrics = case_data_processed.get('metrics', {})
            
            if not case_id:
                raise ValueError("Case ID generation failed")
            
            # Save Database Case Initial Record
            case = create_case(
                case_id=case_id,
                customer_name=customer_info.get('name', 'Unknown'),
                account_number=customer_info.get('account_number', 'Unknown'),
                occupation=customer_info.get('occupation', 'Unknown'),
                stated_income=customer_info.get('stated_income', 0.0)
            )
            
            # Add transactions bulk
            transaction_records = case_data_processed.get('transactions', [])
            
            # The database operation expects 'date', 'type' etc., which 
            # the transaction_processor has already nicely structured in 'transactions'.
            add_transactions_bulk(case_id, transaction_records)
            
            # Update metrics
            update_case_metrics(
                case_id=case_id,
                total_credits=tx_metrics.get('credits', {}).get('total_amount', 0),
                total_debits=tx_metrics.get('debits', {}).get('total_amount', 0),
                transaction_count=case_data_processed.get('data_quality', {}).get('total_transactions', 0),
                unique_senders=tx_metrics.get('credits', {}).get('unique_senders', 0),
                time_period_days=tx_metrics.get('period', {}).get('days', 0)
            )

            # Step 2: Risk Analysis
            logger.info("Running Risk Analysis...")
            risk_results = self.risk_analyzer.analyze_case(case_data_processed)
            
            update_case_risk(
                case_id=case_id,
                risk_score=risk_results.get('risk_score', 0),
                risk_level=risk_results.get('risk_level', 'LOW'),
                flags_triggered=risk_results.get('flags_triggered', 0)
            )

            # Package case data
            case_data = case_data_processed
            case_data['risk_analysis'] = risk_results

            # Step 3: RAG Engine
            logger.info("Retrieving Regulatory Context via RAG...")
            # Automatically handled within generators or we pass it down
            case_data['regulatory_context'] = self.rag_engine.retrieve_regulatory_citations(case_data)

            # Step 4: Generate Narrative (LLaMA or Template)
            logger.info(f"Generating Narrative using {self.generator_name}...")
            # We call Primary Generator
            generation_result = self.primary_generator.generate_narrative(case_data)
            
            narrative = generation_result.get('narrative', '')
            gen_metadata = generation_result.get('metadata', {})
            
            # Step 5: Save Narrative
            logger.info("Saving Narrative...")
            version = save_narrative(
                case_id=case_id,
                content=narrative,
                metadata=gen_metadata,
                created_by='System',
                generation_method=self.generator_name
            )

            # Step 6: Audit Tracker
            logger.info("Logging Audit Trail...")
            audit_trail = self.audit_tracker.generate_audit_trail(
                case_id=case_id,
                case_data=case_data,
                risk_analysis=risk_results,
                narrative_result=generation_result,
                rag_citations=case_data.get('regulatory_context')
            )
            
            save_audit_log(
                case_id=case_id,
                audit_id=f"AUDIT-{case_id}",
                audit_data=audit_trail
            )

            logger.info("Pipeline Complete!")

            return {
                'status': 'SUCCESS',
                'case_id': case_id,
                'risk_level': risk_results['risk_level'],
                'risk_score': risk_results['risk_score'],
                'narrative': narrative,
                'version': version
            }
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
            return {
                'status': 'ERROR',
                'error_message': str(e)
            }
