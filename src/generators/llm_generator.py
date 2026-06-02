import requests
from src.generators.rag_engine import retrieve_context

OLLAMA_URL = "http://localhost:11434/api/generate"


def generate_sar_llm(customer_id, risk, full_data):

    regulations = retrieve_context("AML suspicious activity guidelines")

    customer = full_data["customer"]
    transactions = full_data["transactions"]
    exceptions = full_data["exceptions"]

    # LIMIT DATA (IMPORTANT FOR PERFORMANCE)
    txn_sample = transactions[:100]

    prompt = f"""
You are an AML compliance officer.

Generate a COMPLETE SAR using ONLY the provided data.

--------------------------------------------------

CUSTOMER DETAILS:
{customer}

--------------------------------------------------

TRANSACTION DATA (REAL SAMPLE):
{txn_sample}

--------------------------------------------------

EXCEPTIONS / ALERTS:
{exceptions}

--------------------------------------------------

RISK:
Level: {risk['risk_level']}
Reasons: {risk['reasons']}

--------------------------------------------------

INSTRUCTIONS:

- DO NOT use "Not Available"
- Extract ALL required fields from data:
    - transaction types
    - dates
    - countries
    - channels
    - patterns
- Identify:
    - high-value spikes
    - repeated transactions
    - cross-border flows
    - anomalies from exceptions

--------------------------------------------------

GENERATE SAR IN THIS STRUCTURE:

1. Opening Statement (Purpose of Filing)
2. Customer Information (use customer data)
3. Summary of Suspicious Activity
4. Detailed Transaction Activity (USE REAL DATA)
5. Pattern & Behavior Analysis
6. Source and Destination of Funds
7. Business/Profile Consistency Analysis
8. Suspicion Justification
9. Additional Due Diligence (USE EXCEPTIONS)
10. Actions Taken by Institution
11. Continuation/Status
12. Supporting Documentation Reference
13. Closing Summary

--------------------------------------------------

IMPORTANT:
- Use ACTUAL transaction values
- Mention specific numbers and patterns
- Make it audit-ready
- DO NOT skip any section
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }
    )

    data = response.json()

    if "response" in data:
        output = data["response"]

        # CLEAN FORMAT (remove extra intro text)
        if "1. Opening Statement" in output:
            output = output.split("1. Opening Statement", 1)[1]
            output = "1. Opening Statement" + output

        return output

    elif "error" in data:
        return f"LLM Error: {data['error']}"

    else:
        return f"Unexpected response: {data}"