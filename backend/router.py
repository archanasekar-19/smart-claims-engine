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

    policyholder = data.get("policyholder_name", "the claimant")
    claim_type = data.get("claim_type", "Unknown")
    estimated_damage = data.get("estimated_damage", 0)
    location = data.get("location", "an unspecified location")

    # 1. Fast-track
    if estimated_damage < 25000:
        return (
            "Fast-track",
            f"Estimated damage of ₹{estimated_damage:,} is below the ₹25,000 threshold. "
            f"All mandatory fields are present and no fraud indicators were detected. "
            f"This claim from {policyholder} qualifies for accelerated processing."
        )

    # 2. Investigation Flag
    detected_keywords = [w for w in suspicious_keywords if w in description]

    if detected_keywords:
        keywords_str = ", ".join(f'"{w}"' for w in detected_keywords)
        return (
            "Investigation Flag",
            f"Suspicious keyword(s) {keywords_str} detected in the claim description. "
            f"This {claim_type} claim filed by {policyholder} at {location} has been "
            f"flagged for investigation. A dedicated fraud assessor should review the "
            f"incident narrative and witness statements before proceeding."
        )

    if inconsistencies:
        issues = "; ".join(inconsistencies)
        return (
            "Investigation Flag",
            f"Data inconsistencies detected in this claim from {policyholder}: {issues}. "
            f"The claim cannot be processed until these discrepancies are resolved by an investigator."
        )

    # 3. Manual Review
    if missing_fields:
        fields_str = ", ".join(f.replace("_", " ") for f in missing_fields)
        return (
            "Manual Review",
            f"{len(missing_fields)} mandatory field(s) are missing from this claim: {fields_str}. "
            f"A human adjuster should contact {policyholder} to collect the outstanding "
            f"information before the claim can be routed for processing."
        )

    # 4. Specialist Queue
    if "injury" in claim_type.lower():
        return (
            "Specialist Queue",
            f"Claim type is '{claim_type}', which requires specialist handling. "
            f"This claim from {policyholder} involves personal injury and has been "
            f"assigned to the specialist injury team for medical assessment, "
            f"liability determination, and potential MACT proceedings."
        )

    return (
        "Standard Review",
        f"This {claim_type} claim from {policyholder} at {location} with an estimated "
        f"damage of ₹{estimated_damage:,} meets all mandatory field requirements and "
        f"contains no fraud indicators. Routed for standard adjuster review."
    )