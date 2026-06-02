import sys
import os
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.processors.risk_analyzer import predict_risk
from src.generators.unified_sar_generator import generate_sar_unified

if __name__ == "__main__":
   

    print("\n--- TRANSACTION TYPE ---")
    txn_type_choice = input("Is this a crypto transaction? (yes/no): ").strip().lower()

    # -----------------------------
    # CRYPTO INPUT
    # -----------------------------
    if txn_type_choice == "yes":

        user_case = {
            "type": "crypto",
            "transaction_hash": input("Transaction Hash: "),
            "sender_wallet": input("Sender Wallet: "),
            "receiver_wallet": input("Receiver Wallet: "),
            "crypto_amount": float(input("Crypto Amount: ")),
            "crypto_type": input("Crypto Type (BTC/ETH/etc): "),
            "timestamp": input("Timestamp (YYYY-MM-DD): ")
        }

        # -----------------------------
        # FEATURE MAPPING (CRYPTO → ML)
        # -----------------------------
        features = {
            "kyc_monthly_income": user_case["crypto_amount"] * 2,
            "pep_flag": 0,
            "adverse_media_flag": 0,
            "total_txn_amount": user_case["crypto_amount"],
            "avg_txn_amount": user_case["crypto_amount"],
            "txn_count": 1,
            "unique_countries": 2,
            "high_risk": 1,  # crypto default high-risk
            "exception_count": 1,
            "avg_change_frequency": 1,
            "verified_ratio": 0
        }

    # -----------------------------
    # NORMAL TRANSACTION INPUT
    # -----------------------------
    else:

        user_case = {
            "type": "normal",
            "name": input("Customer Name: "),
            "account_number": input("Account Number: "),
            "txn_amount": float(input("Transaction Amount: ")),
            "country": input("Country: "),
            "txn_type": input("Transaction Type: "),
            "timestamp": input("Transaction Date (YYYY-MM-DD): ")
        }

        features = {
            "kyc_monthly_income": user_case["txn_amount"] * 2,
            "pep_flag": 0,
            "adverse_media_flag": 0,
            "total_txn_amount": user_case["txn_amount"],
            "avg_txn_amount": user_case["txn_amount"],
            "txn_count": 1,
            "unique_countries": 1,
            "high_risk": 1 if user_case["country"].lower() != "india" else 0,
            "exception_count": 0,
            "avg_change_frequency": 1,
            "verified_ratio": 1
        }

    # -----------------------------
    # ML PREDICTION
    # -----------------------------
    
    risk = predict_risk(features)

    # -----------------------------
    # SAR LOGIC
    # -----------------------------
    if risk["risk_level"] == "HIGH":
        sar_report = generate_sar_unified(user_case, risk)
    else:
        sar_report = f"SAR not generated as {risk['risk_level']} risk transaction detected."

    print("\n===== FINAL OUTPUT =====")
    print("Risk:", risk)

    print("\n--- SAR REPORT ---\n")
    print(sar_report)