import os

KNOWLEDGE_PATH = "data/knowledge_base"


def retrieve_context(query, is_crypto=False):

    context = []

    # -----------------------------
    # SELECT FILES BASED ON TYPE
    # -----------------------------
    if is_crypto:
        allowed_files = ["crypto_rules.txt", "sar_narrative_template.txt"]
    else:
        # all files except crypto_rules
        allowed_files = [
            f for f in os.listdir(KNOWLEDGE_PATH)
            if f.endswith(".txt") and f != "crypto_rules.txt"
        ]

    # -----------------------------
    # READ FILES
    # -----------------------------
    for file in allowed_files:

        file_path = os.path.join(KNOWLEDGE_PATH, file)

        if os.path.exists(file_path):

            with open(file_path, "r") as f:
                text = f.read()

                # keyword match (optional but kept)
                if any(word.lower() in text.lower() for word in query.split()):
                    context.append(text[:500])
                else:
                    # fallback → still include (important for structure)
                    context.append(text[:300])

    # -----------------------------
    # FINAL OUTPUT
    # -----------------------------
    if not context:
        return "No relevant regulatory context found."

    return "\n\n".join(context)


class RAGEngine:
    """
    Class wrapper around retrieve_context for OOP usage.
    Used by LlamaNarrativeGenerator.
    """

    def __init__(self, knowledge_path=None):
        self.knowledge_path = knowledge_path or KNOWLEDGE_PATH

    def retrieve(self, query, is_crypto=False):
        return retrieve_context(query, is_crypto=is_crypto)

    def build_context_for_generation(self, case_data):
        """Build context string from case data for LLM prompt."""
        risk = case_data.get('risk_analysis', {})
        query_parts = []
        for flag in risk.get('triggered_flags', []):
            query_parts.append(flag.get('name', ''))
        query = ' '.join(query_parts) if query_parts else 'AML suspicious activity guidelines'
        return self.retrieve(query)