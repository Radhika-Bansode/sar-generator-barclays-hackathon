import os
import logging
from typing import Dict, Any
from src.generators.rag_engine import RAGEngine
from src.generators.narrative_generator_template import TemplateNarrativeGenerator

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False

logger = logging.getLogger(__name__)

class LlamaNarrativeGenerator:
    def __init__(self, rag_engine: RAGEngine = None, model_path: str = None):
        self.rag_engine = rag_engine
        self.model_path = model_path or os.getenv("LLAMA_MODEL_PATH", "/path/to/llama-model.gguf")
        self.llm = None
        self.template_fallback = TemplateNarrativeGenerator(rag_engine=self.rag_engine)
        
        if LLAMA_AVAILABLE and os.path.exists(self.model_path):
            try:
                logger.info(f"Loading LLaMA model from {self.model_path}...")
                self.llm = Llama(
                    model_path=self.model_path,
                    n_ctx=int(os.getenv("LLAMA_N_CTX", 4096)),
                    n_threads=int(os.getenv("LLAMA_N_THREADS", 4)),
                    verbose=False
                )
            except Exception as e:
                logger.error(f"Failed to load LLaMA model: {e}")
                self.llm = None
        else:
            logger.warning("LLaMA model unavailable or path invalid. Will use template fallback.")

    def generate_narrative(self, case_data: Dict[str, Any], include_citations: bool = True) -> Dict[str, Any]:
        """
        Generates SAR narrative using LLaMA.
        If LLaMA isn't available, falls back to the template generator.
        """
        if not self.llm:
            logger.info("Using TemplateNarrativeGenerator as fallback.")
            return self.template_fallback.generate_narrative(case_data, include_citations)
            
        logger.info("Generating narrative with LLaMA...")
        
        # Build prompt
        customer = case_data.get('customer', {})
        metrics = case_data.get('metrics', {})
        risk = case_data.get('risk_analysis', {})
        
        context = ""
        if self.rag_engine and include_citations:
            context = self.rag_engine.build_context_for_generation(case_data)
        
        prompt = self._build_prompt(customer, metrics, risk, context)
        
        try:
            response = self.llm(
                prompt,
                max_tokens=2048,
                temperature=0.2,
                top_p=0.9,
                stop=["### End of SAR Narrative"]
            )
            
            narrative_text = response['choices'][0]['text'].strip()
            
            return {
                'narrative': narrative_text,
                'metadata': {
                    'model': 'llama-cpp',
                    'prompt': prompt,
                    'prompt_tokens': response['usage']['prompt_tokens'],
                    'completion_tokens': response['usage']['completion_tokens'],
                    'total_tokens': response['usage']['total_tokens'],
                    'fallback_used': False
                }
            }
        except Exception as e:
            logger.error(f"Error during LLaMA generation: {e}. Falling back to template.")
            res = self.template_fallback.generate_narrative(case_data, include_citations)
            res['metadata']['fallback_used'] = True
            return res

    def _build_prompt(self, customer: Dict, metrics: Dict, risk: Dict, context: str) -> str:
        """
        Constructs the prompt for the LLaMA model.
        """
        system_instruction = (
            "You are an expert AML Compliance Analyst writing a Suspicious Activity Report (SAR). "
            "Write a factual, professional, chronological narrative based strictly on the provided data and regulatory context. "
            "Do not invent names, dates, or amounts not present in the data."
        )
        
        # Format the data for the prompt
        customer_info = f"Name: {customer.get('name', 'Unknown')}\nOccupation: {customer.get('occupation', 'Unknown')}\nStated Income: {customer.get('stated_income', 0.0)}"
        
        risk_flags = "\n".join([f"- {flag['name']}: {flag['description']} (Severity: {flag['severity']})" for flag in risk.get('triggered_flags', [])])
        
        prompt = f"""[INST] {system_instruction}

### REGULATORY CONTEXT
{context}

### CASE DATA
Customer Profile:
{customer_info}

Risk Assessment:
Risk Level: {risk.get('risk_level')} (Score: {risk.get('risk_score')})
Triggered Red Flags:
{risk_flags}

Transaction Summary:
Total Credits: ${metrics.get('credits', {}).get('total_amount', 0):,.2f}
Total Debits: ${metrics.get('debits', {}).get('total_amount', 0):,.2f}
Total Transactions: {metrics.get('period', {}).get('total_transactions', 0)}
Number of Days: {metrics.get('period', {}).get('days', 0)}

### TASK
Write a complete, professional SAR narrative covering:
1. Introduction & Background
2. Summary of Suspicious Activity
3. Detailed Transaction Analysis
4. Triggered Regulatory/Red Flags
5. Conclusion

Start the narrative immediately below.
[/INST]
"""
        return prompt
