def apply_rules(features):
    rules_triggered = []

    if features["total_txn_amount"] > 300000:
        rules_triggered.append("Large transaction volume")

    if features["high_risk"] == 1:
        rules_triggered.append("High-risk geography")

    if features["exception_count"] > 3:
        rules_triggered.append("Frequent profile changes")

    if features["pep_flag"] == 1:
        rules_triggered.append("Politically exposed person")

    return rules_triggered