import pandas as pd

print("Loading datasets...")

# Load only required columns (IMPORTANT for speed)
customers = pd.read_csv(
    "data/customers.csv",
    usecols=["customer_id", "kyc_monthly_income", "pep_flag", "adverse_media_flag"]
)

transactions = pd.read_csv(
    "data/transactions.csv",
    usecols=["customer_id", "txn_amount", "counterparty_country"]
)

exceptions = pd.read_csv(
    "data/exceptions.csv",
    usecols=["customer_id", "exception_id", "change_frequency_90d", "verified_by_bank"]
)

print("Datasets loaded successfully")


# -----------------------------
# TRANSACTION FEATURES
# -----------------------------

print("Processing transactions...")

txn_group = transactions.groupby("customer_id").agg({
    "txn_amount": ["sum", "mean", "count"],
    "counterparty_country": "nunique"
})

txn_group.columns = [
    "total_txn_amount",
    "avg_txn_amount",
    "txn_count",
    "unique_countries"
]

txn_group = txn_group.reset_index()


# High-risk country flag
high_risk_countries = ["PK", "AE", "SG"]

transactions["high_risk"] = transactions["counterparty_country"].isin(high_risk_countries).astype(int)

high_risk_flag = transactions.groupby("customer_id")["high_risk"].max().reset_index()


# -----------------------------
# EXCEPTION FEATURES
# -----------------------------

print("Processing exceptions...")

exception_group = exceptions.groupby("customer_id").agg({
    "exception_id": "count",
    "change_frequency_90d": "mean",
    "verified_by_bank": "mean"
})

exception_group.columns = [
    "exception_count",
    "avg_change_frequency",
    "verified_ratio"
]

exception_group = exception_group.reset_index()


# -----------------------------
# MERGE
# -----------------------------

print("Merging datasets...")

df = customers.merge(txn_group, on="customer_id", how="left")
df = df.merge(high_risk_flag, on="customer_id", how="left")
df = df.merge(exception_group, on="customer_id", how="left")

df = df.fillna(0)


# -----------------------------
# LABEL CREATION
# -----------------------------

print("Creating labels...")

df["label"] = (
    (df["total_txn_amount"] > 200000) |
    (df["high_risk"] == 1) |
    (df["pep_flag"] == 1) |
    (df["exception_count"] > 2)
).astype(int)


# -----------------------------
# SAVE
# -----------------------------

output_path = "data/training_data.csv"

df.to_csv(output_path, index=False)

print("DONE ✅")
print("Final rows (customers):", len(df))
print("Saved at:", output_path)