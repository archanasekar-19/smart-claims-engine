def route_claim(
    data,
    missing_fields,
    inconsistencies,
    text
):
    description = text.lower()

    suspicious_keywords = [
        "fraud",
        "inconsistent",
        "staged"
    ]

    # 1. Fast-track
    estimated_damage = data.get("estimated_damage", 0)

    if estimated_damage < 25000:
        return (
            "Fast-track",
            "Estimated damage is below ₹25,000"
        )

    # 2. Investigation Flag  ← must come BEFORE missing fields
    if any(word in description for word in suspicious_keywords):
        return (
            "Investigation Flag",
            "Suspicious keywords detected in claim description"
        )

    if inconsistencies:
        return (
            "Investigation Flag",
            "Potential inconsistencies detected in claim data"
        )

    # 3. Manual Review
    if missing_fields:
        return (
            "Manual Review",
            "Mandatory fields are missing"
        )

    # 4. Specialist Queue
    claim_type = data.get("claim_type", "").lower()

    if "injury" in claim_type:
        return (
            "Specialist Queue",
            "Injury claims require specialist handling"
        )

    return (
        "Standard Review",
        "Claim requires standard processing"
    )