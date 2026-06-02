import requests

OLLAMA_URL = "http://localhost:11434/api/generate"


def generate_sar_from_user_input(user_case):

    prompt = f"""
You are an AML compliance officer.

Generate a COMPLETE SAR.

STRICT RULES:
- Use ONLY provided data
- Do NOT assume anything
- Do NOT write "unknown" or "unclear"
- Every section MUST be filled using input

--------------------------------------------------

1. Opening Statement

On {user_case['txn_date']}, a suspicious transaction was detected involving customer {user_case['name']} due to abnormal transaction behavior.

--------------------------------------------------

2. Customer Information

Name: {user_case['name']}
Account Number: {user_case['account_number']}
Account Open Date: {user_case['account_open_date']}
Occupation: {user_case['occupation']}
Country: {user_case['country']}
KYC Status: {user_case['kyc_status']}

--------------------------------------------------

3. Summary of Suspicious Activity

Transaction Amount: {user_case['txn_amount']}
Transaction Type: {user_case['txn_type']}
Channel: {user_case['channel']}

--------------------------------------------------

4. Detailed Transaction Activity

Date: {user_case['txn_date']}
Amount: {user_case['txn_amount']}
Destination Account: {user_case['destination_account']}
Destination Country: {user_case['destination_country']}

--------------------------------------------------

5. Pattern & Behavior Analysis

Typical Range: {user_case['avg_txn_range']}
Transaction Frequency: {user_case['txn_frequency']}

--------------------------------------------------

6. Source and Destination of Funds

Source: {user_case['source_of_funds']}
Destination: {user_case['destination_account']} ({user_case['destination_country']})

--------------------------------------------------

7. Business/Profile Consistency Analysis

The transaction is inconsistent with the customer's occupation as {user_case['occupation']}.

--------------------------------------------------

8. Suspicion Justification

High-value deviation from normal range and unusual transaction pattern.

--------------------------------------------------

9. Additional Due Diligence

Previous Flags: {user_case['previous_flags']}

--------------------------------------------------

10. Actions Taken by Institution

Action Taken: {user_case['action_taken']}

--------------------------------------------------

11. Continuation/Status

Status: {user_case['status']}

--------------------------------------------------

12. Supporting Documentation Reference

All transaction records and KYC details are documented internally.

--------------------------------------------------

13. Closing Summary

This SAR is filed due to suspicious deviation from expected transaction behavior.

--------------------------------------------------

IMPORTANT:
- Do NOT modify values
- Do NOT skip fields
- Keep it professional
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
        return data["response"]
    else:
        return str(data)