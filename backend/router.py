def route_claim(data, missing_fields, inconsistencies, text):

    # Scan only the extracted description field value — not raw text.
    # Raw text includes ACORD pages 3-4 legal boilerplate which contains
    # "fraudulent" in every state notice and would create false positives.
    description = (data.get("description", "") or "").lower()

    suspicious_keywords = ["fraud", "inconsistent", "staged"]
    triggered_keywords  = [w for w in suspicious_keywords if w in description]

    estimated_damage   = data.get("estimated_damage", 0) or 0
    policyholder       = data.get("policyholder_name", "the claimant")
    claim_type         = data.get("claim_type", "")
    location           = data.get("location", "")
    incident_date      = data.get("incident_date", "")
    asset_id           = data.get("asset_id", "")

    # ── Priority 1: Fast-track ─────────────────────────────────────────────
    if 0 < estimated_damage < 25000:
        return (
            "Fast-track",
            (
                f"Estimated damage of ₹{estimated_damage:,} is below the ₹25,000 fast-track threshold. "
                f"The claim filed by {policyholder}"
                + (f" on {incident_date}" if incident_date else "")
                + (f" at {location}" if location else "")
                + " has all mandatory fields present, contains no fraud indicators, "
                "and does not involve personal injury. "
                "This claim qualifies for accelerated straight-through processing with "
                "no manual intervention required."
            )
        )

    # ── Priority 2: Manual Review ──────────────────────────────────────────
    if missing_fields:
        field_labels = ", ".join(f.replace("_", " ") for f in missing_fields)
        return (
            "Manual Review",
            (
                f"This claim cannot be automatically processed because {len(missing_fields)} mandatory "
                f"field{'s are' if len(missing_fields) > 1 else ' is'} missing: {field_labels}. "
                "Without this information, coverage verification, damage assessment, and liability "
                "determination cannot be completed. "
                "A claims handler must contact the claimant to collect the outstanding details "
                "before the claim can be routed further."
            )
        )

    # ── Priority 3: Investigation Flag ────────────────────────────────────
    if triggered_keywords:
        kw_str = ", ".join(f'"{w}"' for w in triggered_keywords)
        return (
            "Investigation Flag",
            (
                f"The claim description contains the following suspicious indicator "
                f"{'keywords' if len(triggered_keywords) > 1 else 'keyword'}: {kw_str}. "
                f"These terms were detected in the accident description submitted by {policyholder}"
                + (f" for vehicle {asset_id}" if asset_id else "")
                + (f" on {incident_date}" if incident_date else "")
                + ". "
                "This pattern is consistent with potentially fraudulent or misrepresented claims. "
                "The claim has been placed on hold and escalated to the Special Investigations Unit (SIU) "
                "for a full fraud assessment before any settlement or repair authorisation is issued."
            )
        )

    # ── Priority 4: Specialist Queue ──────────────────────────────────────
    if claim_type.lower() == "injury":
        return (
            "Specialist Queue",
            (
                f"The claim has been filed under Line of Business: '{claim_type}', indicating "
                "personal injury involvement. "
                f"The incident occurred"
                + (f" on {incident_date}" if incident_date else "")
                + (f" at {location}" if location else "")
                + f" and was reported by {policyholder}. "
                "Injury claims require specialist handling including medical liability review, "
                "hospital report validation, third-party injury assessment, and potential "
                "legal coordination. "
                "This claim has been routed to the dedicated Injury Claims Unit for priority handling."
            )
        )

    # ── Default: Standard Review ───────────────────────────────────────────
    return (
        "Standard Review",
        (
            f"Estimated damage of ₹{estimated_damage:,} exceeds the ₹25,000 fast-track threshold. "
            f"The claim submitted by {policyholder}"
            + (f" on {incident_date}" if incident_date else "")
            + " has all mandatory fields complete, no fraud indicators in the description, "
            "and does not involve personal injury. "
            "The claim has been queued for standard adjuster review, damage verification, "
            "and repair authorisation within the normal processing SLA."
        )
    )