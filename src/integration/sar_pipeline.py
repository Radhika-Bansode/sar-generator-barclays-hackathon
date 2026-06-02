"""
SAR Pipeline Integration Module

Bridges the UI to the backend:
- Feature engineering from user input
- ML risk prediction (XGBoost)
- Conditional SAR generation (HIGH risk only)
- RAG context injection
- LLM narrative generation via Ollama
- Database persistence

Supports both Crypto and Normal transaction flows.
"""

import sys
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.processors.risk_analyzer import predict_risk
from src.generators.unified_sar_generator import generate_sar_unified
from src.generators.rag_engine import retrieve_context

logger = logging.getLogger(__name__)


class SARPipeline:
    """
    End-to-end SAR generation pipeline.

    Flow:
        User Input → Feature Mapping → ML Risk Prediction
        → Conditional SAR Generation → RAG Context → LLM Narrative
    """

    def __init__(self, llama_generator=None):
        self.llama_generator = llama_generator
        logger.info("SARPipeline initialized.")

    # ──────────────────────────────────────────────
    # PUBLIC: Process a CSV-based case (legacy flow)
    # ──────────────────────────────────────────────
    def process_case(self, csv_path: str, customer_info: Dict) -> Dict[str, Any]:
        """
        Legacy CSV-based pipeline used by the old Case Management view.
        Kept for backward compatibility.
        """
        try:
            from src.processors.transaction_processor import TransactionProcessor
            from database.operations import (
                create_case, update_case_risk, update_case_metrics,
                save_narrative, save_audit_log, add_transactions_bulk
            )

            processor = TransactionProcessor()
            case_data = processor.process_csv(csv_path, customer_info)

            case_id_str = case_data['case_id']
            db_case_id = create_case(
                case_id=case_id_str,
                customer_name=customer_info.get('name', 'Unknown'),
                account_number=customer_info.get('account_number', 'N/A'),
                occupation=customer_info.get('occupation', 'N/A'),
                stated_income=customer_info.get('stated_income', 0)
            )

            # Update metrics
            metrics = case_data['metrics']
            update_case_metrics(
                case_id=case_id_str,
                total_credits=metrics['credits']['total_amount'],
                total_debits=metrics['debits']['total_amount'],
                transaction_count=metrics['credits']['count'] + metrics['debits']['count'],
                unique_senders=metrics['credits']['unique_senders'],
                time_period_days=metrics['period']['days'],
                unique_receivers=metrics['debits'].get('unique_receivers', 0),
                has_foreign_transfer='foreign_transfers' in metrics,
                foreign_transfer_amount=metrics.get('foreign_transfers', {}).get('total_amount', 0)
            )

            # Add transactions
            add_transactions_bulk(case_id_str, case_data['transactions'])

            # Build risk features from metrics
            features = {
                "kyc_monthly_income": customer_info.get('stated_income', 0),
                "pep_flag": 0,
                "adverse_media_flag": 0,
                "total_txn_amount": metrics['credits']['total_amount'],
                "avg_txn_amount": metrics['credits']['average_amount'],
                "txn_count": metrics['credits']['count'] + metrics['debits']['count'],
                "unique_countries": 1,
                "high_risk": 1 if 'foreign_transfers' in metrics else 0,
                "exception_count": 0,
                "avg_change_frequency": 1,
                "verified_ratio": 1
            }

            risk = predict_risk(features)
            risk_level = risk['risk_level']
            risk_score = int(risk['risk_score'] * 100)

            update_case_risk(case_id_str, risk_score, risk_level, len(risk.get('reasons', [])))

            # Generate SAR only for HIGH risk
            if risk_level == "HIGH":
                user_case = {
                    "type": "normal",
                    "name": customer_info.get('name', 'Unknown'),
                    "account_number": customer_info.get('account_number', 'N/A'),
                    "txn_amount": metrics['credits']['total_amount'],
                    "country": "India",
                    "txn_type": "Multiple",
                    "timestamp": metrics['period']['start']
                }
                sar_narrative = generate_sar_unified(user_case, risk)

                save_narrative(
                    case_id=case_id_str,
                    content=sar_narrative,
                    metadata={'model': 'llama3', 'risk_score': risk_score},
                    created_by='AI_System',
                    generation_method='llama'
                )

                audit_data = {
                    'data_lineage': {'csv_file': csv_path, 'upload_timestamp': datetime.now().isoformat()},
                    'risk_assessment_trail': {
                        'risk_categorization': {'final_score': risk_score},
                        'rules_triggered': len(risk.get('reasons', [])),
                        'rules_triggered_details': [
                            {'rule_id': f'R{i+1:03d}', 'rule_name': r, 'explanation': r, 'severity': 'HIGH'}
                            for i, r in enumerate(risk.get('reasons', []))
                        ]
                    },
                    'ai_generation_trail': {
                        'model_details': {'model_name': 'llama3'},
                        'generation_parameters': {'generation_time_seconds': 0}
                    }
                }
                save_audit_log(case_id_str, f"AUDIT-{case_id_str}", audit_data)

            from database.models import RiskLevel as RL
            return {
                'status': 'SUCCESS',
                'case_id': case_id_str,
                'risk_level': RL[risk_level],
                'risk_score': risk_score,
                'sar_generated': risk_level == "HIGH"
            }

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return {'status': 'ERROR', 'error_message': str(e)}

    # ──────────────────────────────────────────────
    # PUBLIC: Process a single transaction (new UI)
    # ──────────────────────────────────────────────
    def process_single_transaction(self, user_case: Dict, is_crypto: bool) -> Dict[str, Any]:
        """
        Process a single transaction from the new Case Intake UI.

        Args:
            user_case: Transaction details dict
            is_crypto: True for crypto transactions

        Returns:
            Dict with risk_level, risk_score, sar_report (if HIGH), reasons
        """
        try:
            # ── Feature engineering ──
            if is_crypto:
                amount = float(user_case.get('crypto_amount', 0))
                features = {
                    "kyc_monthly_income": amount * 2.5,
                    "pep_flag": 0,
                    "adverse_media_flag": 0,
                    "total_txn_amount": amount,
                    "avg_txn_amount": amount,
                    "txn_count": 1,
                    "unique_countries": 2,
                    "high_risk": 1 if amount > 50 else (1 if user_case.get("country", "").lower() not in ["india", ""] else 0),
                    "exception_count": 1 if amount > 10 else 0,
                    "avg_change_frequency": 1,
                    "verified_ratio": 0
                }
                user_case["type"] = "crypto"
            else:
                amount = float(user_case.get('txn_amount', 0))
                country = user_case.get('country', 'India')
                features = {
                    "kyc_monthly_income": amount * 0.5,
                    "pep_flag": 0,
                    "adverse_media_flag": 0,
                    "total_txn_amount": amount,
                    "avg_txn_amount": amount,
                    "txn_count": 1,
                    "unique_countries": 1,
                    "high_risk": 1 if country.lower() not in ["india"] else 0,
                    "exception_count": 1 if amount > 500000 else 0,
                    "avg_change_frequency": 1,
                    "verified_ratio": 1
                }
                user_case["type"] = "normal"

            # ── ML prediction ──
            risk = predict_risk(features)
            risk_level = risk['risk_level']
            risk_score = round(risk['risk_score'] * 100, 1)
            reasons = risk.get('reasons', [])

            result = {
                'status': 'SUCCESS',
                'risk_level': risk_level,
                'risk_score': risk_score,
                'reasons': reasons,
                'sar_generated': False,
                'sar_report': None
            }

            # ── Conditional SAR generation ──
            if risk_level == "HIGH":
                sar_report = generate_sar_unified(user_case, risk)
                result['sar_generated'] = True
                result['sar_report'] = sar_report

            # ── Always Persist to database (Auditing) ──
            try:
                from database.operations import (
                    create_case, update_case_risk, save_narrative, save_audit_log
                )
                case_id_str = f"SAR-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                cust_name = user_case.get('name', user_case.get('sender_wallet', 'Crypto User'))
                acct = user_case.get('account_number', user_case.get('transaction_hash', 'N/A'))

                create_case(
                    case_id=case_id_str,
                    customer_name=cust_name,
                    account_number=acct,
                    occupation=user_case.get('occupation', 'N/A'),
                    stated_income=amount
                )
                update_case_risk(case_id_str, int(risk_score), risk_level, len(reasons))
                
                # Only save narrative if generated (High risk)
                if result.get('sar_generated') and result.get('sar_report'):
                    save_narrative(
                        case_id=case_id_str,
                        content=result['sar_report'],
                        metadata={'model': 'llama3', 'risk_score': risk_score, 'is_crypto': is_crypto},
                        created_by='AI_System',
                        generation_method='llama'
                    )

                audit_data = {
                    'data_lineage': {'source': 'UI Case Intake', 'timestamp': datetime.now().isoformat()},
                    'risk_assessment_trail': {
                        'risk_categorization': {'final_score': int(risk_score)},
                        'rules_triggered': len(reasons),
                        'rules_triggered_details': [
                            {'rule_id': f'R{i+1:03d}', 'rule_name': r, 'explanation': r, 'severity': risk_level}
                            for i, r in enumerate(reasons)
                        ]
                    },
                    'ai_generation_trail': {
                        'model_details': {'model_name': 'llama3'},
                        'generation_parameters': {'generation_time_seconds': 0}
                    }
                }
                save_audit_log(case_id_str, f"AUDIT-{case_id_str}", audit_data)
                result['case_id'] = case_id_str
            except Exception as db_err:
                logger.warning(f"DB persistence skipped: {db_err}")
                result['case_id'] = None

            return result

        except Exception as e:
            logger.error(f"Single-transaction pipeline error: {e}")
            return {
                'status': 'ERROR',
                'error_message': str(e),
                'risk_level': 'UNKNOWN',
                'risk_score': 0,
                'sar_generated': False,
                'sar_report': None
            }
