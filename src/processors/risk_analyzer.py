import joblib
import pandas as pd

model = joblib.load("models/xgboost_risk_model.pkl")

def predict_risk(features_dict):
    print(f"DEBUG: Processing features: {features_dict}")
    df = pd.DataFrame([features_dict])
    prob = model.predict_proba(df)[0][1]
    reasons = get_reasons(features_dict)
    print(f"DEBUG: Triggered reasons: {reasons}")

    # ── Heuristic adjustment for imbalanced model ──
    # If no flags are triggered, the base model prob should be lowered
    if not reasons:
        if features_dict.get("total_txn_amount", 0) < 100000:
            prob *= 0.2  # Significant drop for low amount + no flags
        else:
            prob *= 0.5  # drop for no flags

    # Cap probability
    prob = max(0.01, min(0.999, prob))

    if prob > 0.75:
        level = "HIGH"
    elif prob > 0.4:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "risk_level": level,
        "risk_score": round(prob, 3),
        "reasons": reasons
    }


def get_reasons(f):
    reasons = []

    # High Transaction Volume: Lowered threshold for better detection
    if f.get("total_txn_amount", 0) > 100000:
        reasons.append("High transaction volume")

    # High Risk Jurisdiction
    if f.get("high_risk") == 1:
        reasons.append("High-risk country involvement")

    # Stated Income Inconsistency
    if f.get("total_txn_amount", 0) > f.get("kyc_monthly_income", 0):
        reasons.append("Stated income inconsistency (potential layering)")

    # Multiple Exceptions (e.g., amount-based flags)
    if f.get("exception_count", 0) > 0:
        reasons.append("Multiple exceptions detected in patterns")

    # PEP Exposure
    if f.get("pep_flag") == 1:
        reasons.append("Politically exposed person")

    return reasons