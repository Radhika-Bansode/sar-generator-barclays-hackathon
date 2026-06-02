import pandas as pd

HIGH_RISK_COUNTRIES = ["PK", "AE", "SG"]

def build_features(transactions_df, customer_row, exceptions_df):
    """
    transactions_df → all transactions for ONE customer
    customer_row → single row from customers.csv
    exceptions_df → all exceptions for that customer
    """

    # -----------------------------
    # TRANSACTION FEATURES
    # -----------------------------
    total_txn_amount = transactions_df["txn_amount"].sum()
    avg_txn_amount = transactions_df["txn_amount"].mean()
    txn_count = len(transactions_df)
    unique_countries = transactions_df["counterparty_country"].nunique()

    transactions_df["high_risk"] = transactions_df["counterparty_country"].isin(HIGH_RISK_COUNTRIES).astype(int)
    high_risk = transactions_df["high_risk"].max()

    # -----------------------------
    # EXCEPTION FEATURES
    # -----------------------------
    exception_count = len(exceptions_df)

    if exception_count > 0:
        avg_change_frequency = exceptions_df["change_frequency_90d"].mean()
        verified_ratio = exceptions_df["verified_by_bank"].mean()
    else:
        avg_change_frequency = 0
        verified_ratio = 0

    # -----------------------------
    # CUSTOMER FEATURES
    # -----------------------------
    features = {
        "kyc_monthly_income": customer_row["kyc_monthly_income"],
        "pep_flag": customer_row["pep_flag"],
        "adverse_media_flag": customer_row["adverse_media_flag"],
        "total_txn_amount": total_txn_amount,
        "avg_txn_amount": avg_txn_amount,
        "txn_count": txn_count,
        "unique_countries": unique_countries,
        "high_risk": high_risk,
        "exception_count": exception_count,
        "avg_change_frequency": avg_change_frequency,
        "verified_ratio": verified_ratio
    }

    return features