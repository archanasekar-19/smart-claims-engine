"""
Field mappings, patterns, and helper utilities for ACORD 2 claim extraction.
All patterns and configurations are defined here.
"""
import re

MANDATORY_FIELDS = [
    "policy_number", "policyholder_name", "effective_dates",
    "incident_date", "incident_time", "location", "description",
    "claimant", "contact_details", "asset_type", "asset_id",
    "estimated_damage", "claim_type", "attachments", "initial_estimate",
]

# ── helpers ────────────────────────────────────────────────────────────────

_EMPTY = re.compile(
    r"^\s*(\[not provided[^\]]*\]|\[missing[^\]]*\]|\[none[^\]]*\]"
    r"|not provided|not disclosed|unknown|n/?a|none|--+|tbd|pending)\s*$",
    re.I,
)
_REDACTED = re.compile(r"x{2,}", re.I)


def is_empty(v) -> bool:
    """Check if value is empty or marked as missing."""
    if v is None:
        return True
    v = str(v).strip()
    if not v:
        return True
    if _EMPTY.match(v):
        return True
    clean = re.sub(r"[^a-zA-Z0-9]", "", v)
    return bool(clean) and all(c.upper() == "X" for c in clean)


def clean(v) -> str:
    """Clean whitespace from value."""
    return str(v).strip() if v else ""


def normalize(s: str) -> str:
    """Normalize string to uppercase with single spaces."""
    return re.sub(r"\s+", " ", str(s)).strip().upper()


def parse_money(s: str):
    """
    Parse dollar / rupee / plain number from a string.
    Returns int or None.
    """
    if not s:
        return None
    s = str(s).strip()
    
    # Try lakh format (Indian)
    m = re.search(r"(\d+(?:\.\d+)?)\s*lakh", s, re.I)
    if m:
        return int(float(m.group(1)) * 100_000)
    
    # Try currency prefix
    m = re.search(r"(?:INR|Rs\.?|₹|\$)\s*([\d,]+(?:\.\d+)?)", s, re.I)
    if m:
        return int(float(m.group(1).replace(",", "")))
    
    # Try plain number with commas
    m = re.search(r"\b(\d[\d,]{2,})\b", s)
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except ValueError:
            pass
    
    return None


# ===========================================================================
# ACORD 2 FIELD MAPPING
# ===========================================================================

# Maps ACORD form field_id → our internal key.
# ONLY named fields are used here — labels printed on the ACORD 2 form.
# Unnamed positional fields (Text1, Text7, etc.) are NOT mapped here.
# Their values are written into REMARKS as "Key: Value" lines.

ACORD_FIELD_MAP = {
    # ── Policy / insured ──────────────────────────────────────────────────
    "POLICY NUMBER": "policy_number",
    "CARRIER": "carrier",
    "NAIC CODE": "naic_code",
    "NAME OF INSURED First Middle Last": "policyholder_name",
    "INSUREDS MAILING ADDRESS": "insured_address",
    "DATE OF BIRTH": "insured_dob",
    "PHONE  CELL HOME BUS PRIMARY": "contact_phone",
    "PRIMARY EMAIL ADDRESS": "contact_email",

    # ── Contact ───────────────────────────────────────────────────────────
    "NAME OF CONTACT First Middle Last": "claimant",

    # ── Loss location ─────────────────────────────────────────────────────
    "STREET LOCATION OF LOSS": "location_street",
    "CITY STATE ZIP": "location_city",
    "COUNTRY": "location_country",
    "POLICE OR FIRE DEPARTMENT CONTACTED": "police_contacted",
    "REPORT NUMBER": "report_number",

    # ── Incident ──────────────────────────────────────────────────────────
    "DESCRIPTION OF ACCIDENT ACORD 101 Additional Remarks Schedule may be attached if more space is required": "description",

    # ── Vehicle ───────────────────────────────────────────────────────────
    "VEH": "veh_num",
    "YEAR": "vehicle_year",
    "MAKE": "vehicle_make",
    "TYPE BODY": "asset_type",
    "MODEL": "vehicle_model",
    "VIN": "vin",
    "PLATE NUMBER": "plate_number",
    "STATE": "vehicle_state",

    # ── Driver ────────────────────────────────────────────────────────────
    "Employee family etc RELATION TO INSURED": "relation_to_insured",
    "DRIVERS LICENSE NUMBER": "driver_license",
    "PURPOSE OF USE": "purpose_of_use",

    # ── Damage ────────────────────────────────────────────────────────────
    "DESCRIBE DAMAGE": "describe_damage",
    "WHERE CAN VEHICLE BE SEEN": "where_vehicle_seen",
    "WHEN CAN VEHICLE BE SEEN": "when_vehicle_seen",
    "OTHER INSURANCE ON VEHICLE  CARRIER": "other_ins_carrier",

    # ── Page 2 remarks ────────────────────────────────────────────────────
    # REMARKS is where unmapped values are stored as "Key: Value" lines
    "REMARKS ACORD 101 Additional Remarks Schedule may be attached if more space is required": "remarks",
}


# ===========================================================================
# TEXT EXTRACTION PATTERNS
# ===========================================================================

TEXT_PATTERNS = {
    "policy_number": [
        r"Policy\s*(?:No(?:\.)?|Number|#)[:\s]*([A-Z0-9\-/]+)",
        r"(?:FNOL|File|Claim)\s*(?:No(?:\.)?|Number|#)[:\s]*([A-Z0-9\-/]+)",
        r"^[A-Z]{2,4}\d{6,}",  # Common format like SAFE123456
    ],
    "policyholder_name": [
        r"Policyholder\s*Name[:\s]+(.+?)(?:\n|$)",
        r"Name\s+of\s+Insured[:\s]+(.+?)(?:\n|$)",
        r"Insured\s*(?:Name)?[:\s]+(.+?)(?:\n|$)",
    ],
    "effective_dates": [
        r"Policy\s+(?:Effective|Period|Duration)[:\s]+(.+?)(?:\n|$)",
        r"Effective\s+From[:\s]+(.+?)(?:\s+To|$)",
        r"Effective\s*Date[:\s]+(.+?)(?:\n|$)",
        r"(\d{1,2}/\d{1,2}/\d{4})\s+(?:to|-|–)\s+(\d{1,2}/\d{1,2}/\d{4})",
    ],
    "incident_date": [
        r"(?:Date\s+)?(?:of\s+)?(?:Incident|Loss|Accident|Claim)[:\s]+(.+?)(?:\n|$)",
        r"Incident\s*Date[:\s]+(.+?)(?:\n|$)",
        r"(?:on\s+)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(\w+\s+\d{1,2},?\s+\d{4})",  # January 15, 2024
    ],
    "incident_time": [
        r"Time\s+of\s+(?:Incident|Loss|Accident)[:\s]+(\d{1,2}[:.]\d{2}\s*(?:AM|PM)?)",
        r"(?:at\s+)?(\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm)?)",
        r"(?:time|occurred)[:\s]*(\d{1,2}[:.]\d{2})",
    ],
    "location": [
        r"(?:Location|Site)\s+of\s+(?:Incident|Loss|Accident)[:\s]+(.+?)(?:\n|$)",
        r"(?:Incident\s+)?Location[:\s]+(.+?)(?:\n|$)",
        r"(?:Street\s+)?Location[:\s]+(.+?)(?:\n|$)",
    ],
    "claimant": [
        r"^Claimant\s+([A-Za-z][A-Za-z\s]+?)(?:\s*\(|$)",
        r"^Claimant(?:\s+Name)?[:\s]+([A-Za-z][A-Za-z\s]+?)(?:\s*\[|$)",
        r"Claimant[:\s]+(.+?)(?:\n|$)",
    ],
    "contact_details": [
        r"(?:Contact|Primary)\s*(?:Phone|Mobile|Tel)[:\s]+([\+\d\s\(\)\-X]+)",
        r"(?:Phone|Mobile|Tel)[:\s]+([\+\d\s\(\)\-X]+)",
        r"Email[:\s]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        r"(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})",
    ],
    "asset_type": [
        r"(?:Asset|Vehicle|Property)\s*Type[:\s]+(.+?)(?:\n|$)",
        r"TYPE\s+BODY[:\s]+(.+?)(?:\n|$)",
        r"(?:Body|Car|Bike)\s+Type[:\s]+(.+?)(?:\n|$)",
    ],
    "asset_id": [
        r"V\.I\.N\.[:\s]+([A-Z0-9]{5,})",
        r"VIN[:\s]+([A-Z0-9]{5,})",
        r"Asset\s*(?:ID|No)[:\s]+([A-Z0-9]+)",
        r"PLATE\s*NUMBER[:\s]+([A-Z0-9\-]+)",
        r"(?:Number\s+Plate|Registration)[:\s]+([A-Z0-9\-]+)",
    ],
    "claim_type": [
        r"(?:Claim|Loss)\s+Type[:\s]+(.+?)(?:\n|$)",
        r"(?:Nature|Cause)\s+of\s+(?:Loss|Damage|Claim)[:\s]+(.+?)(?:\n|$)",
        r"LINE\s+OF\s+BUSINESS[:\s]+(.+?)(?:\n|$)",
        r"(?:Collision|Damage|Theft|Fire)[:\s]*(.+?)(?:\n|$)",
    ],
    "attachments": [
        r"^Attachments?\s+(.+?)(?:\n|$)",
        r"Documents?\s+(?:Submitted|Attached|Provided)[:\s]+(.+?)(?:\n|$)",
        r"REMARKS[:\s]+(.+?)(?:\n|$)",
    ],
}

MONEY_PATTERNS = {
    "estimated_damage": [
        r"Estimated\s+Damage[:\s]+(.+)",
        r"Damage\s+Estimate[:\s]+(.+)",
        r"ESTIMATE\s+AMOUNT[:\s]+\$?([\d,\.]+)",
        r"Loss\s+Amount[:\s]+(.+)",
    ],
    "initial_estimate": [
        r"Initial\s+Estimate[:\s]+(.+)",
        r"Workshop\s+Estimate[:\s]+(.+)",
        r"Approx(?:imate)?\.?\s+(?:INR|₹|\$)\s*([\d,]+)",
    ],
}


def find_in_remarks(form_fields: dict, pattern: str, group_fmt: str = "{1}") -> str:
    """Search the REMARKS field for a regex pattern."""
    sources = [
        form_fields.get(
            "REMARKS ACORD 101 Additional Remarks Schedule may be attached if more space is required", ""
        ),
    ]
    rx = re.compile(pattern, re.I)
    for src in sources:
        if not src:
            continue
        m = rx.search(src)
        if m:
            if group_fmt == "{1}":
                return m.group(1).strip()
            # multi-group format e.g. "{1} – {2}"
            result = group_fmt
            for i, g in enumerate(m.groups(), 1):
                result = result.replace(f"{{{i}}}", g or "")
            return result.strip()
    return ""


def match_field(text: str, patterns: list):
    """Find and return first match from list of patterns."""
    for pat in patterns:
        m = re.search(pat, text, re.I | re.M)
        if m:
            val = clean(m.group(1))
            val = re.split(r"\s*[\[\|]", val)[0].strip()
            val = re.sub(r"\s{2,}", " ", val)
            if not is_empty(val):
                return val
    return None


def match_money(text: str, patterns: list):
    """Find and return first monetary value from list of patterns."""
    for pat in patterns:
        m = re.search(pat, text, re.I | re.M)
        if m:
            snippet = m.group(1)
            nums = re.findall(r"[\d,]+(?:\.\d+)?", snippet)
            for n in nums:
                v = parse_money(n)
                if v and v > 0:
                    return v
    return None


def extract_multiline_description(text: str):
    """Extract multi-line description section from narrative text."""
    _stop = re.compile(
        r"^\s*([A-Z]\.\s+[A-Z]|■|MISSING:|INSURED\s+VEHICLE"
        r"|OWNER'S\s+NAME|ESTIMATE\s+AMOUNT|Claimant[\s:]"
        r"|Asset\s+Type|Claim\s+Type|Attachments?|REMARKS)",
        re.I,
    )
    start = re.search(
        r"(?:DESCRIPTION\s+OF\s+ACCIDENT|Description|Nature\s+of\s+(?:Loss|Damage))"
        r"(?:[^:\n]*)?\s+(.+)",
        text, re.I | re.M,
    )
    if not start:
        return None
    
    lines = [start.group(1).strip()]
    for line in text[start.end():].split("\n"):
        if _stop.match(line):
            break
        s = line.strip()
        if s:
            lines.append(s)
        elif lines:
            break
    
    full = " ".join(lines).strip()
    return re.sub(r"\s{2,}", " ", full) or None


def find_missing_fields(extracted_fields: dict) -> list:
    """
    Identify missing mandatory fields from the extracted data.
    Returns list of field names that are empty or missing.
    """
    missing = []
    for field in MANDATORY_FIELDS:
        value = extracted_fields.get(field)
        if is_empty(value):
            missing.append(field)
    return missing


def find_inconsistencies(extracted_fields: dict) -> list:
    """
    Detect data inconsistencies and quality issues.
    Returns list of inconsistency dictionaries with 'field', 'issue', and 'severity'.
    """
    issues = []
    
    # Check date consistency: incident_date should not be after report_date
    incident_date = extracted_fields.get("incident_date", "")
    report_date = extracted_fields.get("report_date", "")
    if incident_date and report_date and incident_date > report_date:
        issues.append({
            "field": "dates",
            "issue": "Incident date is after report date",
            "severity": "high"
        })
    
    # Check if policyholder_name matches claimant
    policyholder = (extracted_fields.get("policyholder_name") or "").lower()
    claimant = (extracted_fields.get("claimant") or "").lower()
    if policyholder and claimant and policyholder != claimant:
        # Only flag if they're significantly different (not just typos)
        if similarity_score(policyholder, claimant) < 0.7:
            issues.append({
                "field": "claimant",
                "issue": f"Claimant differs from policyholder",
                "severity": "medium"
            })
    
    # Check if estimated damage is reasonable (not negative, not suspiciously high)
    estimated_damage = extracted_fields.get("estimated_damage", "")
    if estimated_damage:
        try:
            damage_amount = float(re.sub(r'[^\d.]', '', str(estimated_damage)))
            if damage_amount < 0:
                issues.append({
                    "field": "estimated_damage",
                    "issue": "Negative damage amount",
                    "severity": "high"
                })
            elif damage_amount > 10000000:  # More than 10M (adjust threshold as needed)
                issues.append({
                    "field": "estimated_damage",
                    "issue": "Unusually high damage claim",
                    "severity": "medium"
                })
        except:
            pass
    
    # Check if contact details are provided
    contact = extracted_fields.get("contact_details", "")
    if is_empty(contact):
        issues.append({
            "field": "contact_details",
            "issue": "No contact information provided",
            "severity": "high"
        })
    
    return issues


def similarity_score(s1: str, s2: str) -> float:
    """Calculate string similarity score (0-1)."""
    if not s1 or not s2:
        return 0.0
    
    # Simple character overlap approach
    s1_chars = set(s1.replace(" ", ""))
    s2_chars = set(s2.replace(" ", ""))
    
    if not s1_chars and not s2_chars:
        return 1.0
    
    overlap = len(s1_chars & s2_chars)
    total = len(s1_chars | s2_chars)
    
    return overlap / total if total > 0 else 0.0
