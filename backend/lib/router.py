"""
router.py — Intelligent claim routing engine
Routes claims to appropriate departments/handlers based on:
- Extracted field data
- Missing critical information
- Data inconsistencies
- Claim characteristics (type, amount, complexity)
"""

from typing import Dict, List, Tuple, Any
import re


def route_claim(
    extracted_fields: Dict[str, Any],
    missing_fields: List[str],
    inconsistencies: List[Dict[str, str]],
    full_text: str,
) -> Tuple[str, str]:
    """
    Simple routing rules based on claim characteristics:
    1. If estimated damage < £25,000 → Fast-track
    2. If any mandatory field is missing → Manual review
    3. If description contains fraud keywords → Investigation
    4. If claim type = injury → Specialist Queue
    
    Returns:
        (recommended_route, reasoning)
    """
    reasons = []
    
    # ========== RULE 1: Check for missing mandatory fields ==========
    MANDATORY_FIELDS = ["policy_number", "policyholder_name", "incident_date", "claim_type"]
    critical_missing = [f for f in missing_fields if f in MANDATORY_FIELDS]
    
    if critical_missing:
        route = "manual_review"
        reasons.append(f"Missing mandatory fields: {', '.join(critical_missing)}")
        reasoning = " | ".join(reasons)
        return route, reasoning
    
    # ========== RULE 2: Check for fraud indicators in description ==========
    fraud_keywords = ["fraud", "inconsistent", "staged", "planned", "fake", "intentional"]
    description = (extracted_fields.get("description", "") + " " + full_text).lower()
    
    fraud_found = [kw for kw in fraud_keywords if kw in description]
    if fraud_found:
        route = "investigation"
        reasons.append(f"Fraud keywords detected: {', '.join(fraud_found)}")
        reasoning = " | ".join(reasons)
        return route, reasoning
    
    # ========== RULE 3: Check claim type for injury ==========
    claim_type = extracted_fields.get("claim_type", "").lower()
    
    if any(kw in claim_type for kw in ["injury", "bodily injury", "personal injury", "casualty"]):
        route = "specialist_queue"
        reasons.append("Injury claim requires specialist handling")
        reasoning = " | ".join(reasons)
        return route, reasoning
    
    # ========== RULE 4: Check estimated damage amount ==========
    estimated_damage = extract_amount(extracted_fields.get("estimated_damage", ""))
    
    if estimated_damage and estimated_damage < 25000:
        route = "fast_track"
        reasons.append(f"Damage estimate £{estimated_damage:,.2f} < £25,000 threshold")
        reasoning = " | ".join(reasons)
        return route, reasoning
    
    # ========== DEFAULT: Manual review for higher amounts or unclear cases ==========
    route = "manual_review"
    if estimated_damage:
        reasons.append(f"Damage estimate £{estimated_damage:,.2f} requires manual review")
    else:
        reasons.append("No damage estimate available - routing to manual review")
    
    reasoning = " | ".join(reasons)
    return route, reasoning





def extract_amount(amount_str: str) -> float:
    """Extract numeric amount from string"""
    if not amount_str:
        return 0.0
    
    # Remove common currency symbols and text
    cleaned = re.sub(r'[^\d.,]', '', amount_str)
    cleaned = cleaned.replace(',', '')
    
    try:
        return float(cleaned)
    except ValueError:
        return 0.0
