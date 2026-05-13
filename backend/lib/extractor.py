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

    # Step 2: Initialize result.
    # The parser returns two kinds of keys:
    #   a) ACORD field_ids (e.g. "PLATE NUMBER") → map via ACORD_FIELD_MAP
    #   b) Already-resolved internal keys (e.g. "policy_number", "estimated_damage")
    #      for fields the parser resolved spatially — use directly.
    result = {}

    # 2a: map named ACORD field_ids
    for acord_key, internal_key in ACORD_FIELD_MAP.items():
        value = form_fields.get(acord_key, "")
        if not is_empty(value):
            result[internal_key] = clean(value)

    # 2b: merge already-resolved internal keys from spatial parser
    _INTERNAL_KEYS = set(ACORD_FIELD_MAP.values()) | {
        "policy_number", "claim_type", "estimated_damage",
        "incident_date", "incident_time", "claim_number", "agency_name",
    }
    for key, value in form_fields.items():
        if key in _INTERNAL_KEYS and not is_empty(value) and key not in result:
            result[key] = clean(value)

    # Step 2b: Coerce monetary fields from Text45 to int
    from lib.config import parse_money
    for money_key in ("estimated_damage", "initial_estimate"):
        raw = result.get(money_key)
        if raw and isinstance(raw, str):
            parsed_val = parse_money(raw)
            if parsed_val:
                result[money_key] = parsed_val

    # Step 2c: Validate incident_time — reject impossible times like "38:20"
    raw_time = result.get("incident_time", "")
    if raw_time:
        t_match = re.match(r"(\d{1,2})[:\.](\d{2})", raw_time)
        if t_match:
            h, m = int(t_match.group(1)), int(t_match.group(2))
            if h > 23 or m > 59:
                del result["incident_time"]
        else:
            del result["incident_time"]

    # Step 2d: Build composite location from parts if not directly mapped
    if "location" not in result or is_empty(result.get("location")):
        street = result.get("location_street", "")
        city = result.get("location_city", "")
        if street or city:
            result["location"] = ", ".join(p for p in [street, city] if p)

    # Step 2e: Promote plate_number → asset_id if asset_id is missing
    if is_empty(result.get("asset_id")):
        plate = result.get("plate_number", "")
        vin   = result.get("vin", "")
        if plate and not is_empty(plate):
            result["asset_id"] = plate
        elif vin and not is_empty(vin):
            result["asset_id"] = vin

    # Step 3: Apply TEXT_PATTERNS for missing fields
    for field_name, patterns in TEXT_PATTERNS.items():
        if field_name not in result or is_empty(result.get(field_name)):
            matched = match_field(text, patterns)
            if matched:
                result[field_name] = matched

    # Step 3b: Re-validate incident_time after TEXT_PATTERNS (may have introduced bad values)
    raw_time2 = result.get("incident_time", "")
    if raw_time2:
        t_match2 = re.match(r"(\d{1,2})[:\.](\d{2})", raw_time2)
        if t_match2:
            h2, m2 = int(t_match2.group(1)), int(t_match2.group(2))
            if h2 > 23 or m2 > 59:
                del result["incident_time"]
        else:
            del result["incident_time"]

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

    # ── contact_details — consolidate from phone + email form fields ───────
    # Priority: form fields are the most reliable source; do this before text scan.
    if is_empty(result.get("contact_details")):
        parts = []
        phone = result.get("contact_phone", "")
        email = result.get("contact_email", "")
        # Only include phone if it has at least 7 digits
        if phone and not is_empty(phone) and len(re.sub(r"\D", "", phone)) >= 7:
            parts.append(phone)
        if email and not is_empty(email):
            parts.append(email)
        if parts:
            result["contact_details"] = " | ".join(parts)

    # ── policy_number fallbacks ────────────────────────────────────────────
    if is_empty(result.get("policy_number")):
        patterns = [
            r"Policy\s*No[.:]?\s*([A-Z0-9][A-Z0-9\-/]{4,})",
            r"Policy\s*Number[:\s]+([A-Z0-9][A-Z0-9\-/]{4,})",
            r"^[A-Z]{2,4}\d{6,}",  # e.g. SAFE123456
        ]
        for pat in patterns:
            m = re.search(pat, text, re.I | re.M)
            if m:
                val = clean(m.group(1) if m.lastindex else m.group(0))
                if not is_empty(val) and len(val) >= 6:
                    result["policy_number"] = val
                    break

    # ── effective_dates fallbacks ──────────────────────────────────────────
    if is_empty(result.get("effective_dates")):
        # REMARKS typically contains "Policy Period: DD/MM/YYYY to DD/MM/YYYY."
        patterns = [
            r"Policy\s+Period:\s*(\d{1,2}/\d{1,2}/\d{4})\s+to\s+(\d{1,2}/\d{1,2}/\d{4})",
            r"(\d{1,2}/\d{1,2}/\d{4})\s+to\s+(\d{1,2}/\d{1,2}/\d{4})",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.I | re.M)
            if m:
                val = f"{m.group(1)} to {m.group(2)}"
                if not is_empty(val):
                    result["effective_dates"] = val
                    break

    # ── incident_date fallbacks ────────────────────────────────────────────
    if is_empty(result.get("incident_date")):
        # Only accept values that look like actual dates — not addresses
        patterns = [
            r"Date\s+of\s+(?:Loss|Incident|Accident)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"incident[^\n]*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.I | re.M)
            if m:
                val = clean(m.group(1))
                if not is_empty(val) and re.match(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", val):
                    result["incident_date"] = val
                    break
        # Last resort: use Text1 form field directly (it's the Date of Loss field)
        if is_empty(result.get("incident_date")):
            t1 = form_fields.get("Text1", "")
            if t1 and re.match(r"\d{1,2}/\d{1,2}/\d{4}", t1.strip()):
                result["incident_date"] = t1.strip()

    # ── incident_time fallbacks ────────────────────────────────────────────
    if is_empty(result.get("incident_time")):
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

    # ── contact_details — text-based fallback if still missing ────────────
    if is_empty(result.get("contact_details")):
        contacts = []
        for pat in [r"(?:Phone|Tel|Mobile|Contact)[:\s]+([\+\d][\d\s\(\)\-X]{6,})",
                    r"(\+91[\s-]?\d{10})", r"\b(\d{10})\b"]:
            m = re.search(pat, text, re.I)
            if m:
                val = clean(m.group(1))
                # Require at least 7 digits
                if len(re.sub(r"\D", "", val)) >= 7:
                    contacts.append(val)
                    break
        for pat in [r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"]:
            m = re.search(pat, text, re.I)
            if m:
                contacts.append(clean(m.group(1)))
                break
        if contacts:
            result["contact_details"] = " | ".join(contacts)

    # ── claim_type fallbacks ───────────────────────────────────────────────
    if is_empty(result.get("claim_type")):
        patterns = [
            r"(?:Claim|Loss)\s+Type[:\s]+(.+?)(?:\n|$)",
            r"(?:Nature|Cause)\s+of\s+(?:Loss|Damage)[:\s]+(.+?)(?:\n|$)",
            r"LINE\s+OF\s+BUSINESS[:\s]+(.+?)(?:\n|$)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.I | re.M)
            if m:
                val = clean(m.group(1))
                # Reject PDF copyright/watermark lines
                if not is_empty(val) and "FormsBoss" not in val and "Impressive Publishing" not in val:
                    result["claim_type"] = val
                    break

        # Use Text8 (Line of Business field) directly from form
        if is_empty(result.get("claim_type")):
            lob = form_fields.get("Text8", "")
            if lob and not is_empty(lob):
                result["claim_type"] = lob.strip()

        # Infer from asset_type as last resort
        if is_empty(result.get("claim_type")) and result.get("asset_type"):
            asset = result["asset_type"].lower()
            if any(w in asset for w in ["vehicle", "car", "hatchback", "suv", "bike", "truck"]):
                result["claim_type"] = "Motor Vehicle Damage"
            elif any(w in asset for w in ["property", "building", "house"]):
                result["claim_type"] = "Property Damage"

    # ── attachments fallback from REMARKS ──────────────────────────────────
    if is_empty(result.get("attachments")):
        remarks = form_fields.get(
            "REMARKS ACORD 101 Additional Remarks Schedule may be attached if more space is required", ""
        )
        if remarks:
            # Try explicit "Attachments: ..." sub-line first
            m = re.search(r"Attachments?:\s*(.+?)(?:\.|ROUTING|$)", remarks, re.I)
            if m:
                val = clean(m.group(1))
                if not is_empty(val):
                    result["attachments"] = val
            # Try "Photographs attached..." style
            if is_empty(result.get("attachments")):
                m = re.search(r"(Photographs?\s+attached[^.]*)", remarks, re.I)
                if m:
                    result["attachments"] = clean(m.group(1))

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