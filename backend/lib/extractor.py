"""
Enhanced extraction engine for ACORD 2 claim forms.
Fixes missing field extraction by:
1. Using both form fields AND text pattern matching
2. Improving regex patterns for narrative text
3. Fallback strategies for missing critical fields
"""

import re
from typing import Dict, Any, Optional
from lib.parser import extract
from lib.config import (
    ACORD_FIELD_MAP,
    TEXT_PATTERNS,
    MONEY_PATTERNS,
    match_field,
    match_money,
    clean,
    is_empty,
    find_in_remarks,
)


def extract_claim(file_path: str) -> Dict[str, Any]:
    """
    Extract all claim fields from PDF/TXT.
    Combines form fields + text pattern extraction for maximum coverage.
    """
    
    # Step 1: Parse the file
    parsed = extract(file_path)
    form_fields = parsed.get("form_fields", {})
    text = parsed.get("text", "")
    
    # Step 2: Initialize result with form fields
    result = {}
    for acord_key, internal_key in ACORD_FIELD_MAP.items():
        value = form_fields.get(acord_key, "")
        if not is_empty(value):
            result[internal_key] = clean(value)
    
    # Step 3: Apply TEXT_PATTERNS for missing fields
    for field_name, patterns in TEXT_PATTERNS.items():
        if field_name not in result or is_empty(result.get(field_name)):
            matched = match_field(text, patterns)
            if matched:
                result[field_name] = matched
    
    # Step 4: Apply MONEY_PATTERNS for monetary fields
    for field_name, patterns in MONEY_PATTERNS.items():
        if field_name not in result or not result.get(field_name):
            matched = match_money(text, patterns)
            if matched:
                result[field_name] = matched
    
    # Step 5: Extract multi-line description if missing
    if "description" not in result or is_empty(result.get("description")):
        from lib.config import extract_multiline_description
        desc = extract_multiline_description(text)
        if desc:
            result["description"] = desc
    
    # Step 6: Apply FALLBACK strategies for critical missing fields
    result = _apply_fallbacks(result, text, form_fields)
    
    return result


def _apply_fallbacks(result: Dict[str, Any], text: str, form_fields: Dict[str, str]) -> Dict[str, Any]:
    """
    Apply fallback extraction strategies for stubborn missing fields.
    """
    
    # ── policy_number fallbacks ────────────────────────────────────────────
    if is_empty(result.get("policy_number")):
        # Try to extract from description or remarks
        patterns = [
            r"Policy\s*(?:No(?:\.)?|Number|#)[:\s]*([A-Z0-9\-/]+)",
            r"(?:FNOL|File|Claim)\s*(?:No(?:\.)?|Number|#)[:\s]*([A-Z0-9\-/]+)",
            r"^[A-Z]{2,4}\d{6,}",  # Common format: SAFE123456
        ]
        for pat in patterns:
            m = re.search(pat, text, re.I | re.M)
            if m:
                val = clean(m.group(1) if m.lastindex else m.group(0))
                if not is_empty(val):
                    result["policy_number"] = val
                    break
    
    # ── effective_dates fallbacks ──────────────────────────────────────────
    if is_empty(result.get("effective_dates")):
        # Look for date ranges in the text
        patterns = [
            r"Policy\s+(?:Effective|Period|Duration)[:\s]+(.+?)(?:\n|$)",
            r"Effective\s+From[:\s]+(.+?)(?:\s+To|$)",
            r"(\d{1,2}/\d{1,2}/\d{4})\s+(?:to|-|–)\s+(\d{1,2}/\d{1,2}/\d{4})",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.I | re.M)
            if m:
                if m.lastindex == 2:
                    # Two-group match (from – to)
                    val = f"{m.group(1)} to {m.group(2)}"
                else:
                    val = clean(m.group(1))
                
                if not is_empty(val):
                    result["effective_dates"] = val
                    break
    
    # ── incident_date fallbacks ────────────────────────────────────────────
    if is_empty(result.get("incident_date")):
        # Extract from description or narrative
        patterns = [
            r"(?:on\s+)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",  # 15/1/2024 or 15-01-24
            r"(\w+\s+\d{1,2},?\s+\d{4})",  # January 15, 2024
            r"incident[^\n]*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.I | re.M)
            if m:
                val = clean(m.group(1))
                if not is_empty(val):
                    result["incident_date"] = val
                    break
    
    # ── incident_time fallbacks ────────────────────────────────────────────
    if is_empty(result.get("incident_time")):
        # Look for time patterns
        patterns = [
            r"(?:at\s+)?(\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm)?)",
            r"(?:time|occurred)\s*[:\s]*(\d{1,2}[:.]\d{2}\s*(?:AM|PM)?)",
            r"(\d{1,2}:\d{2}(?::\d{2})?)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.I | re.M)
            if m:
                val = clean(m.group(1))
                if not is_empty(val):
                    result["incident_time"] = val
                    break
    
    # ── contact_details fallbacks ──────────────────────────────────────────
    if is_empty(result.get("contact_details")):
        # Try phone, email, or both
        phone_patterns = [
            r"(?:Phone|Tel|Mobile|Contact)[:\s]+([\+\d\s\(\)\-X]+)",
            r"(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})",  # 10-digit US/standard
            r"(\+91[\s-]?\d{10})",  # Indian format
        ]
        email_patterns = [
            r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        ]
        
        contacts = []
        for pat in phone_patterns:
            m = re.search(pat, text, re.I)
            if m:
                contacts.append(clean(m.group(1)))
        
        for pat in email_patterns:
            m = re.search(pat, text, re.I)
            if m:
                contacts.append(clean(m.group(1)))
        
        if contacts:
            result["contact_details"] = " | ".join(contacts[:2])
    
    # ── claim_type fallbacks ───────────────────────────────────────────────
    if is_empty(result.get("claim_type")):
        # Infer from description or asset type
        patterns = [
            r"(?:Claim|Loss)\s+Type[:\s]+(.+?)(?:\n|$)",
            r"(?:Nature|Cause)\s+of\s+(?:Loss|Damage)[:\s]+(.+?)(?:\n|$)",
            r"LINE\s+OF\s+BUSINESS[:\s]+(.+?)(?:\n|$)",
        ]
        
        for pat in patterns:
            m = re.search(pat, text, re.I | re.M)
            if m:
                val = clean(m.group(1))
                if not is_empty(val):
                    result["claim_type"] = val
                    break
        
        # If still missing, infer from asset_type
        if is_empty(result.get("claim_type")) and result.get("asset_type"):
            asset = result["asset_type"].lower()
            if "vehicle" in asset or "car" in asset or "hatchback" in asset:
                result["claim_type"] = "Motor Vehicle Damage"
            elif "property" in asset or "building" in asset:
                result["claim_type"] = "Property Damage"
            else:
                result["claim_type"] = "Claim"
    
    return result


def extract_and_validate(file_path: str, mandatory_fields: list = None) -> Dict[str, Any]:
    """
    Extract claim and return results with validation.
    """
    if mandatory_fields is None:
        from lib.config import MANDATORY_FIELDS
        mandatory_fields = MANDATORY_FIELDS
    
    extracted = extract_claim(file_path)
    
    # Find missing fields
    missing = []
    for field in mandatory_fields:
        if field not in extracted or is_empty(extracted.get(field)):
            missing.append(field)
    
    return {
        "extractedFields": extracted,
        "missingFields": missing,
        "isComplete": len(missing) == 0,
    }
