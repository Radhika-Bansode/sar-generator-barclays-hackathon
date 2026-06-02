REQUIRED_SECTIONS = [
    "Opening Statement",
    "Customer Information",
    "Summary of Suspicious Activity",
    "Detailed Transaction Activity",
    "Pattern & Behavior Analysis",
    "Source and Destination of Funds",
    "Business/Profile Consistency Analysis",
    "Suspicion Justification",
    "Additional Due Diligence",
    "Actions Taken by Institution",
    "Continuation",
    "Supporting Documentation",
    "Closing Summary"
]


def validate_sar(sar_text):
    missing = []

    for section in REQUIRED_SECTIONS:
        if section.lower() not in sar_text.lower():
            missing.append(section)

    return missing