def enforce_template(llm_text):

    sections = [
        "1. Opening Statement",
        "2. Customer Information",
        "3. Summary of Suspicious Activity",
        "4. Detailed Transaction Activity",
        "5. Pattern & Behavior Analysis",
        "6. Source and Destination of Funds",
        "7. Business/Profile Consistency Analysis",
        "8. Suspicion Justification",
        "9. Additional Due Diligence",
        "10. Actions Taken by Institution",
        "11. Continuation/Status",
        "12. Supporting Documentation Reference",
        "13. Closing Summary"
    ]

    formatted = "\n".join(sections) + "\n\n" + llm_text

    return formatted