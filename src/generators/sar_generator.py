def generate_sar(customer_id, risk, features, rules):

    narrative = f"""
Suspicious Activity Report (SAR)

Customer ID: {customer_id}

Risk Classification: {risk['risk_level']}
Risk Score: {risk['risk_score']}

Summary:
The system has identified this customer as high risk based on behavioral analysis and rule-based indicators.

Key Risk Indicators:
"""

    for r in risk["reasons"]:
        narrative += f"\n- {r}"

    narrative += "\n\nRegulatory Rule Triggers:\n"

    for rule in rules:
        narrative += f"- {rule}\n"

    narrative += """

Conclusion:
The customer's activity shows patterns consistent with potential financial crime such as structuring or cross-border laundering.

Recommendation:
This case should be escalated for further investigation and regulatory reporting.
"""

    return narrative