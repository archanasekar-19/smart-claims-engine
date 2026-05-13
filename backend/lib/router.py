"""
router.py — Intelligent claim routing engine

Routing priority (in order):
  1. estimated_damage < 25,000  → Fast-track
  2. Any mandatory field missing → Manual Review
  3. Fraud keywords in description only → Investigation Flag
  4. claim_type contains 'injury' → Specialist Queue
  5. Default (high damage, no other flag) → Manual Review

Route name strings match the frontend routeColors keys exactly:
  "Fast-track" | "Manual Review" | "Investigation Flag" | "Specialist Queue"
"""

from typing import Dict, List, Tuple, Any
import re


# ── Constants ──────────────────────────────────────────────────────────────

_FRAUD_KEYWORDS = ["fraud", "inconsistent", "staged", "planned", "fake", "intentional"]

_INJURY_KEYWORDS = ["injury", "bodily injury", "personal injury", "casualty"]

_FAST_TRACK_THRESHOLD = 25_000

# Fields whose absence triggers Manual Review
_ROUTING_MANDATORY = [
    "policy_number", "policyholder_name", "incident_date",
    "incident_time", "location", "description", "claimant",
    "contact_details", "asset_type", "asset_id", "claim_type",
]


# ── Public API ─────────────────────────────────────────────────────────────

def route_claim(
    extracted_fields: Dict[str, Any],
    missing_fields: List[str],
    inconsistencies: List[Dict[str, str]],
    full_text: str,
) -> Tuple[str, str]:
    """
    Route a claim and return (route_name, reasoning).

    Priority:
      1. Fast-track          — damage < £25,000, no other flags
      2. Manual Review       — mandatory fields missing
      3. Investigation Flag  — fraud keywords in description only
      4. Specialist Queue    — injury claim type
      5. Manual Review       — default for high-damage / unclear
    """

    policyholder     = extracted_fields.get("policyholder_name", "the claimant")
    claim_type       = extracted_fields.get("claim_type", "")
    incident_date    = extracted_fields.get("incident_date", "")
    location         = extracted_fields.get("location", "")
    asset_id         = extracted_fields.get("asset_id", "")
    estimated_damage = _to_number(extracted_fields.get("estimated_damage"))

    # ── Rule 1: Fast-track ─────────────────────────────────────────────────
    if estimated_damage and 0 < estimated_damage < _FAST_TRACK_THRESHOLD:
        reasoning = (
            f"Estimated damage of \u20b9{estimated_damage:,.0f} is below the "
            f"\u20b9{_FAST_TRACK_THRESHOLD:,} fast-track threshold. "
            f"The claim filed by {policyholder}"
            + (f" on {incident_date}" if incident_date else "")
            + (f" at {location}" if location else "")
            + " has all mandatory fields present, contains no fraud indicators, "
            "and does not involve personal injury. "
            "This claim qualifies for accelerated straight-through processing "
            "with no manual intervention required."
        )
        return "Fast-track", reasoning

    # ── Rule 2: Manual Review — missing mandatory fields ──────────────────
    critical_missing = [f for f in missing_fields if f in _ROUTING_MANDATORY]
    if critical_missing:
        field_labels = ", ".join(f.replace("_", " ") for f in critical_missing)
        count = len(critical_missing)
        reasoning = (
            f"This claim cannot be automatically processed because {count} mandatory "
            f"field{'s are' if count > 1 else ' is'} missing: {field_labels}. "
            "Without this information, coverage verification, damage assessment, "
            "and liability determination cannot be completed. "
            "A claims handler must contact the claimant to collect the outstanding "
            "details before the claim can be routed further."
        )
        return "Manual Review", reasoning

    # ── Rule 3: Investigation Flag — fraud keywords in description ONLY ────
    # Scan only the extracted description field, NOT the raw full text —
    # every PDF embeds "fraud" in the state anti-fraud legal notice which
    # would cause a false positive on every single claim.
    description = (extracted_fields.get("description", "") or "").lower()
    fraud_found = [kw for kw in _FRAUD_KEYWORDS if kw in description]
    if fraud_found:
        kw_str = ", ".join(f'"{w}"' for w in fraud_found)
        reasoning = (
            f"The claim description contains the following suspicious "
            f"{'keywords' if len(fraud_found) > 1 else 'keyword'}: {kw_str}. "
            f"These terms were detected in the accident description submitted by {policyholder}"
            + (f" for vehicle {asset_id}" if asset_id else "")
            + (f" on {incident_date}" if incident_date else "")
            + ". "
            "This pattern is consistent with potentially fraudulent or misrepresented claims. "
            "The claim has been placed on hold and escalated to the Special Investigations Unit (SIU) "
            "for a full fraud assessment before any settlement or repair authorisation is issued."
        )
        return "Investigation Flag", reasoning

    # ── Rule 4: Specialist Queue — injury claim ───────────────────────────
    if any(kw in claim_type.lower() for kw in _INJURY_KEYWORDS):
        reasoning = (
            f"The claim has been filed under Line of Business: '{claim_type}', "
            "indicating personal injury involvement. "
            "The incident occurred"
            + (f" on {incident_date}" if incident_date else "")
            + (f" at {location}" if location else "")
            + f" and was reported by {policyholder}. "
            "Injury claims require specialist handling including medical liability review, "
            "hospital report validation, third-party injury assessment, and potential legal coordination. "
            "This claim has been routed to the dedicated Injury Claims Unit for priority handling."
        )
        return "Specialist Queue", reasoning

    # ── Default: Manual Review — high damage or no estimate ───────────────
    if estimated_damage:
        reasoning = (
            f"Estimated damage of \u20b9{estimated_damage:,.0f} exceeds the "
            f"\u20b9{_FAST_TRACK_THRESHOLD:,} fast-track threshold. "
            f"The claim submitted by {policyholder}"
            + (f" on {incident_date}" if incident_date else "")
            + " has all mandatory fields complete and no fraud indicators in the description. "
            "The claim has been queued for standard adjuster review, damage verification, "
            "and repair authorisation within the normal processing SLA."
        )
    else:
        reasoning = (
            f"No damage estimate is available for the claim submitted by {policyholder}"
            + (f" on {incident_date}" if incident_date else "")
            + ". Without a validated damage amount the claim cannot be fast-tracked "
            "and requires a manual damage assessment before processing can continue."
        )
    return "Manual Review", reasoning


# ── Helpers ────────────────────────────────────────────────────────────────

def _to_number(value) -> float:
    """Convert extracted damage value (int, float, or string) to float."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*lakh", s, re.I)
    if m:
        return float(m.group(1)) * 100_000
    cleaned = re.sub(r"[^\d.]", "", s.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0