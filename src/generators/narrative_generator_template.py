"""
Template-based SAR Narrative Generator (fallback when LLaMA is unavailable)
"""


def generate_narrative(customer_id, risk_level, risk_score, reasons):

    text = f"""
Suspicious Activity Report (SAR)

Customer ID: {customer_id}

The system has identified this customer as {risk_level} risk with a confidence score of {risk_score}.

Key indicators include:
"""

    for r in reasons:
        text += f"\n- {r}"

    text += """

The observed transaction patterns deviate from expected behavior and may indicate potential financial crime.

This case should be reviewed by the compliance team for further investigation.
"""

    return text


class TemplateNarrativeGenerator:
    """
    Class wrapper for template-based SAR generation.
    Used as fallback by LlamaNarrativeGenerator.
    """

    def __init__(self, rag_engine=None):
        self.rag_engine = rag_engine

    def generate_narrative(self, case_data, include_citations=True):
        customer = case_data.get('customer', {})
        risk = case_data.get('risk_analysis', {})
        metrics = case_data.get('metrics', {})

        customer_name = customer.get('name', 'Unknown')
        risk_level = risk.get('risk_level', 'UNKNOWN')
        risk_score = risk.get('risk_score', 0)
        reasons = [f.get('name', '') for f in risk.get('triggered_flags', [])]

        narrative_text = generate_narrative(customer_name, risk_level, risk_score, reasons)

        return {
            'narrative': narrative_text,
            'metadata': {
                'model': 'template',
                'fallback_used': True,
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            }
        }