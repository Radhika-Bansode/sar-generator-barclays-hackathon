"""
Unified SAR Generator
Generates SAR narratives using Ollama LLM (llama3) with RAG context.
Uses the 13-section SAR format matching user_input_sar.py standard.
Falls back to structured template if Ollama is unavailable.
"""

import requests
import logging
from datetime import datetime
from src.generators.rag_engine import retrieve_context

OLLAMA_URL = "http://localhost:11434/api/generate"
logger = logging.getLogger(__name__)


def generate_sar_unified(user_case, risk):
    """
    Generate a SAR narrative using LLM (Ollama/llama3) with RAG context.
    Uses the 13-section SAR format from user_input_sar.py.
    """

    is_crypto = user_case.get("type") == "crypto"
    regulations = retrieve_context("AML rules", is_crypto=is_crypto)

    risk_level = risk.get('risk_level', 'HIGH')
    reasons = risk.get('reasons', [])
    reasons_text = "\n".join([f"- {r}" for r in reasons])

    if is_crypto:
        # Build prompt for crypto
        prompt = _build_crypto_prompt(user_case, risk, regulations)
    else:
        # Build prompt using the exact user_input_sar.py format
        prompt = _build_normal_prompt(user_case, risk, regulations)

    # TRY OLLAMA LLM
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=120
        )

        data = response.json()

        if "response" in data and len(data["response"].strip()) > 100:
            output = data["response"]

            # Clean format - strip LLM intro text
            if "1. Opening Statement" in output:
                output = output.split("1. Opening Statement", 1)[1]
                output = "1. Opening Statement" + output

            logger.info("SAR generated via Ollama LLM (llama3) - 13 section format.")
            return output
        else:
            logger.warning("Ollama returned insufficient response. Using template fallback.")
            return _generate_template_sar(user_case, risk, is_crypto)

    except requests.exceptions.ConnectionError:
        logger.warning("Ollama not reachable. Using template fallback.")
        return _generate_template_sar(user_case, risk, is_crypto)
    except requests.exceptions.Timeout:
        logger.warning("Ollama timed out. Using template fallback.")
        return _generate_template_sar(user_case, risk, is_crypto)
    except Exception as e:
        logger.error(f"LLM error: {e}. Using template fallback.")
        return _generate_template_sar(user_case, risk, is_crypto)


def _build_normal_prompt(user_case, risk, regulations):
    """Build prompt for normal banking SAR using user_input_sar.py format."""

    # Extract all fields with safe defaults
    name = user_case.get('name', 'Unknown')
    account = user_case.get('account_number', 'N/A')
    acct_open = user_case.get('account_open_date', 'N/A')
    occupation = user_case.get('occupation', 'N/A')
    country = user_case.get('country', 'India')
    kyc = user_case.get('kyc_status', 'verified')
    amount = user_case.get('txn_amount', 0)
    txn_type = user_case.get('txn_type', 'N/A')
    channel = user_case.get('channel', 'Online')
    txn_date = user_case.get('txn_date', user_case.get('timestamp', 'N/A'))
    dest_acct = user_case.get('destination_account', 'N/A')
    dest_country = user_case.get('destination_country', 'India')
    avg_range = user_case.get('avg_txn_range', 'N/A')
    frequency = user_case.get('txn_frequency', 'N/A')
    source = user_case.get('source_of_funds', 'N/A')
    prev_flags = user_case.get('previous_flags', 'no')
    action = user_case.get('action_taken', 'N/A')
    status = user_case.get('status', 'Under Review')

    risk_level = risk.get('risk_level', 'HIGH')
    reasons = risk.get('reasons', [])
    reasons_text = ", ".join(reasons)

    return f"""You are an AML compliance officer.

Generate a COMPLETE SAR using ONLY the provided data.

STRICT RULES:
- Use ONLY provided data
- Do NOT assume anything
- Do NOT write "unknown" or "unclear"
- Every section MUST be filled using input

--------------------------------------------------

1. Opening Statement

On {txn_date}, a suspicious transaction was detected involving customer {name} due to abnormal transaction behavior.

--------------------------------------------------

2. Customer Information

Name: {name}
Account Number: {account}
Account Open Date: {acct_open}
Occupation: {occupation}
Country: {country}
KYC Status: {kyc}

--------------------------------------------------

3. Summary of Suspicious Activity

Transaction Amount: {amount}
Transaction Type: {txn_type}
Channel: {channel}

--------------------------------------------------

4. Detailed Transaction Activity

Date: {txn_date}
Amount: {amount}
Destination Account: {dest_acct}
Destination Country: {dest_country}

--------------------------------------------------

5. Pattern & Behavior Analysis

Typical Range: {avg_range}
Transaction Frequency: {frequency}

--------------------------------------------------

6. Source and Destination of Funds

Source: {source}
Destination: {dest_acct} ({dest_country})

--------------------------------------------------

7. Business/Profile Consistency Analysis

The transaction is inconsistent with the customer's occupation as {occupation}.

--------------------------------------------------

8. Suspicion Justification

Risk Level: {risk_level}
Risk Reasons: {reasons_text}

--------------------------------------------------

9. Additional Due Diligence

Previous Flags: {prev_flags}

--------------------------------------------------

10. Actions Taken by Institution

Action Taken: {action}

--------------------------------------------------

11. Continuation/Status

Status: {status}

--------------------------------------------------

12. Supporting Documentation Reference

All transaction records and KYC details are documented internally.

--------------------------------------------------

13. Closing Summary

This SAR is filed due to suspicious deviation from expected transaction behavior.

--------------------------------------------------

Regulatory Context:
{regulations}

IMPORTANT:
- Do NOT modify values
- Do NOT skip fields
- Keep it professional
"""


def _build_crypto_prompt(user_case, risk, regulations):
    """Build prompt for crypto SAR."""

    sender = user_case.get('sender_wallet', 'N/A')
    receiver = user_case.get('receiver_wallet', 'N/A')
    tx_hash = user_case.get('transaction_hash', 'N/A')
    amount = f"{user_case.get('crypto_amount', 0)} {user_case.get('crypto_type', 'BTC')}"
    txn_date = user_case.get('timestamp', 'N/A')
    risk_level = risk.get('risk_level', 'HIGH')
    reasons = risk.get('reasons', [])
    reasons_text = ", ".join(reasons)

    return f"""You are an AML compliance officer.

Generate a COMPLETE SAR for a cryptocurrency transaction.

STRICT RULES:
- Use ONLY provided data
- Every section MUST be filled

--------------------------------------------------

1. Opening Statement

On {txn_date}, a suspicious cryptocurrency transaction was detected involving wallet {sender} due to abnormal transaction behavior.

2. Customer Information

Sender Wallet: {sender}
Transaction Hash: {tx_hash}
Country: Blockchain Network

3. Summary of Suspicious Activity

Amount: {amount}
Transaction Type: Cryptocurrency Transfer

4. Detailed Transaction Activity

Date: {txn_date}
Amount: {amount}
Sender: {sender}
Receiver: {receiver}
Hash: {tx_hash}

5. Pattern & Behavior Analysis

Cryptocurrency transaction pattern analysis based on blockchain activity.

6. Source and Destination of Funds

Source Wallet: {sender}
Destination Wallet: {receiver}

7. Business/Profile Consistency Analysis

Cryptocurrency transaction requires additional KYC verification.

8. Suspicion Justification

Risk Level: {risk_level}
Reasons: {reasons_text}

9. Additional Due Diligence

Blockchain analytics and wallet cluster analysis required.

10. Actions Taken by Institution

Transaction flagged for regulatory reporting and enhanced monitoring.

11. Continuation/Status

Status: Under Review

12. Supporting Documentation Reference

Blockchain transaction records and wallet analysis documented internally.

13. Closing Summary

This SAR is filed due to suspicious cryptocurrency transaction activity.

--------------------------------------------------

Regulatory Context:
{regulations}

IMPORTANT:
- Do NOT modify values
- Keep it professional
"""


def _generate_template_sar(user_case, risk, is_crypto):
    """
    Template-based SAR using the 13-section format.
    Fallback when Ollama LLM is unavailable.
    """
    risk_level = risk.get('risk_level', 'HIGH')
    risk_score = risk.get('risk_score', 'N/A')
    reasons = risk.get('reasons', [])
    reasons_text = "\n".join([f"- {r}" for r in reasons]) if reasons else "- Anomalous transaction detected."

    if is_crypto:
        sender = user_case.get('sender_wallet', 'N/A')
        receiver = user_case.get('receiver_wallet', 'N/A')
        tx_hash = user_case.get('transaction_hash', 'N/A')
        amount = f"{user_case.get('crypto_amount', 0)} {user_case.get('crypto_type', 'BTC')}"
        txn_date = user_case.get('timestamp', datetime.now().strftime('%Y-%m-%d'))

        return f"""1. Opening Statement

On {txn_date}, a suspicious cryptocurrency transaction was detected involving wallet {sender} due to abnormal transaction behavior.

2. Customer Information

Sender Wallet: {sender}
Transaction Hash: {tx_hash}
Country: Blockchain Network
Risk Level: {risk_level}

3. Summary of Suspicious Activity

Amount: {amount}
Transaction Type: Cryptocurrency Transfer
Risk Classification: {risk_level}

4. Detailed Transaction Activity

Date: {txn_date}
Amount: {amount}
Sender Wallet: {sender}
Receiver Wallet: {receiver}
Transaction Hash: {tx_hash}

5. Pattern & Behavior Analysis

The cryptocurrency transaction exhibits patterns inconsistent with typical wallet behavior. Automated monitoring has identified deviations from established baselines.

6. Source and Destination of Funds

Source Wallet: {sender}
Destination Wallet: {receiver}

7. Business/Profile Consistency Analysis

Cryptocurrency transaction requires additional KYC verification. Wallet activity is inconsistent with expected patterns.

8. Suspicion Justification

{reasons_text}

The combination of these factors indicates a {risk_level} risk level requiring regulatory reporting.

9. Additional Due Diligence

Blockchain analytics and wallet cluster analysis have been initiated. Previous Flags: no

10. Actions Taken by Institution

Transaction flagged for regulatory reporting. SAR filing initiated. Wallet placed under enhanced monitoring.

11. Continuation/Status

Status: Under Review - Pending regulatory filing

12. Supporting Documentation Reference

All blockchain transaction records and wallet analysis are documented internally.

13. Closing Summary

This SAR is filed due to suspicious cryptocurrency transaction activity involving wallet {sender} on {txn_date} for {amount}. Risk classification: {risk_level}."""

    else:
        name = user_case.get('name', 'Unknown')
        account = user_case.get('account_number', 'N/A')
        acct_open = user_case.get('account_open_date', 'N/A')
        occupation = user_case.get('occupation', 'N/A')
        country = user_case.get('country', 'India')
        kyc = user_case.get('kyc_status', 'verified')
        amount = user_case.get('txn_amount', 0)
        txn_type = user_case.get('txn_type', 'N/A')
        channel = user_case.get('channel', 'Online')
        txn_date = user_case.get('txn_date', user_case.get('timestamp', datetime.now().strftime('%Y-%m-%d')))
        dest_acct = user_case.get('destination_account', 'N/A')
        dest_country = user_case.get('destination_country', 'India')
        avg_range = user_case.get('avg_txn_range', 'N/A')
        frequency = user_case.get('txn_frequency', 'N/A')
        source = user_case.get('source_of_funds', 'N/A')
        prev_flags = user_case.get('previous_flags', 'no')
        action = user_case.get('action_taken', 'N/A')
        status = user_case.get('status', 'Under Review')

        return f"""1. Opening Statement

On {txn_date}, a suspicious transaction was detected involving customer {name} due to abnormal transaction behavior.

2. Customer Information

Name: {name}
Account Number: {account}
Account Open Date: {acct_open}
Occupation: {occupation}
Country: {country}
KYC Status: {kyc}

3. Summary of Suspicious Activity

Transaction Amount: {amount}
Transaction Type: {txn_type}
Channel: {channel}

4. Detailed Transaction Activity

Date: {txn_date}
Amount: {amount}
Destination Account: {dest_acct}
Destination Country: {dest_country}

5. Pattern & Behavior Analysis

Typical Range: {avg_range}
Transaction Frequency: {frequency}

6. Source and Destination of Funds

Source: {source}
Destination: {dest_acct} ({dest_country})

7. Business/Profile Consistency Analysis

The transaction is inconsistent with the customer's occupation as {occupation}.

8. Suspicion Justification

{reasons_text}

9. Additional Due Diligence

Previous Flags: {prev_flags}

10. Actions Taken by Institution

Action Taken: {action}

11. Continuation/Status

Status: {status}

12. Supporting Documentation Reference

All transaction records and KYC details are documented internally.

13. Closing Summary

This SAR is filed due to suspicious deviation from expected transaction behavior. The transaction involving {name} on {txn_date} for amount {amount} has been classified as {risk_level} risk."""