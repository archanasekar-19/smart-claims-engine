import re

MANDATORY_FIELDS = [
    "policy_number",
    "policyholder_name",
    "effective_dates",
    "incident_date",
    "incident_time",
    "location",
    "description",
    "claimant",
    "contact_details",
    "asset_type",
    "asset_id",
    "estimated_damage",
    "claim_type",
    "attachments",
    "initial_estimate",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOT_PROVIDED_PATTERNS = re.compile(
    r"^\s*("
    r"\[not provided[^\]]*\]"
    r"|\[missing[^\]]*\]"
    r"|\[none[^\]]*\]"
    r"|not provided"
    r"|not disclosed"
    r"|unknown"
    r"|n/?a"
    r"|none"
    r"|--+"
    r"|tbd"
    r"|pending"
    r")\s*$",
    re.IGNORECASE,
)

REDACTED_PATTERN = re.compile(r"x{2,}", re.IGNORECASE)


def is_empty_value(val: str) -> bool:
    """Return True when a matched string is a placeholder / not-provided marker."""
    if not val or not val.strip():
        return True
    if NOT_PROVIDED_PATTERNS.match(val.strip()):
        return True
    # Fully redacted  e.g. "98XXX XXXXX"
    clean = re.sub(r"[^a-zA-Z0-9]", "", val)
    if clean and all(c.upper() == "X" for c in clean):
        return True
    return False


def clean_value(val: str) -> str:
    return val.strip() if val else ""


def parse_inr(text: str):
    """
    Extract the first INR / lakh / rupee amount from a string.
    Handles:
        INR 1,20,000  |  INR 75,000  |  1.2 lakhs  |  ₹3,20,000
        'around 1.2 lakhs'  |  'INR 1,20,000 (civil work only)'
    Returns int or None.
    """
    # Lakh shorthand: "1.2 lakhs", "2 lakh"
    lakh = re.search(r"(\d+(?:\.\d+)?)\s*lakh", text, re.IGNORECASE)
    if lakh:
        return int(float(lakh.group(1)) * 100_000)

    # Numeric with optional INR / ₹ prefix and Indian comma formatting
    num = re.search(
        r"(?:INR|₹|Rs\.?)\s*([\d,]+)",
        text,
        re.IGNORECASE,
    )
    if num:
        return int(num.group(1).replace(",", ""))

    # Plain number ≥ 3 digits (last resort, only called when context is monetary)
    plain = re.search(r"\b(\d{3,})\b", text)
    if plain:
        return int(plain.group(1).replace(",", ""))

    return None


# ---------------------------------------------------------------------------
# Multi-pattern field extraction
# ---------------------------------------------------------------------------

FIELD_PATTERNS = {
    "policy_number": [
        r"Policy\s*Number[:\s]+([A-Z0-9\-/]+)",
        r"FNOL\s*#[:\s]*([A-Z0-9\-/]+)",
        r"Claim\s*(?:No|Number|Ref)[:\s]+([A-Z0-9\-/]+)",
    ],
    "policyholder_name": [
        r"Policyholder\s*Name[:\s]+(.+)",
        r"Policy\s*Holder[:\s]+(.+)",
        r"Insured\s*Name[:\s]+(.+)",
        r"Name\s+of\s+Insured[:\s]+(.+)",
    ],
    "effective_dates": [
        r"Policy\s*Effective\s*Date[:\s]+(.+)",
        r"Effective\s*Date[:\s]+(.+)",
        r"Effective\s*Dates?[:\s]+(.+)",
        r"Policy\s*Period[:\s]+(.+)",
        r"Cover(?:age)?\s*Period[:\s]+(.+)",
        # Combine effective + expiry into one field if both on same line
        r"(?:From|Start)[:\s]+(.+?)\s+(?:To|End|Until|Expiry)[:\s]+.+",
    ],
    "incident_date": [
        r"Date\s+of\s+(?:Incident|Loss|Accident|Event|Occurrence)[:\s]+(.+)",
        r"Incident\s*Date[:\s]+(.+)",
        r"Date[:\s]+(.+?)(?:\s*\(|$)",
        r"Loss\s*Date[:\s]+(.+)",
        r"Accident\s*Date[:\s]+(.+)",
    ],
    "incident_time": [
        r"Time\s+of\s+(?:Incident|Loss|Accident|Event)[:\s]+(\d{1,2}[:.]\d{2}\s*(?:AM|PM)?)",
        r"Incident\s*Time[:\s]+(\d{1,2}[:.]\d{2}\s*(?:AM|PM)?)",
        r"Time[:\s]+(\d{1,2}[:.]\d{2}\s*(?:AM|PM)?)",
        r"Approx(?:imate)?\s*[Tt]ime[:\s]+(\d{1,2}[:.]\d{2}\s*(?:AM|PM)?)",
    ],
    "location": [
        r"Location\s+of\s+(?:Incident|Loss|Accident)[:\s]+(.+)",
        r"(?:Incident\s+)?Location[:\s]+(.+)",
        r"Address\s+of\s+(?:Loss|Incident)[:\s]+(.+)",
        r"Place\s+of\s+(?:Incident|Loss|Accident)[:\s]+(.+)",
    ],
    "claimant": [
        r"^Claimant\s+([A-Za-z][A-Za-z\s]+?)(?:\s*\(|$)",
        r"^Claimant(?:\s+Name)?[:\s]+([A-Za-z][A-Za-z\s]+?)(?:\s*\(|\s*\[|$)",
        r"Filed\s+By[:\s]+(.+)",
        r"Reported\s+By[:\s]+(.+)",
    ],
    "contact_details": [
        r"Contact\s*Phone[:\s]+([\+\d\s\(\)\-X]+)",
        r"(?:Mobile|Phone|Tel(?:ephone)?)[:\s]+([\+\d\s\(\)\-X]+)",
        r"Contact\s+(?:Details?|Info(?:rmation)?|Number)[:\s]+(.+)",
    ],
    "asset_type": [
        r"Asset\s*Type[:\s]+(.+)",
        r"Type\s+of\s+(?:Asset|Vehicle|Property)[:\s]+(.+)",
        r"Vehicle\s*Type[:\s]+(.+)",
        r"Property\s*Type[:\s]+(.+)",
    ],
    "asset_id": [
        r"Asset\s*(?:ID|No|Number)[:\s]+([A-Z0-9]+)",
        r"Vehicle\s*(?:Reg(?:istration)?|Number|No)[:\s]+([A-Z0-9]+)",
        r"Registration\s*(?:Number|No)[:\s]+([A-Z0-9]+)",
        r"VIN[:\s]+([A-Z0-9]+)",
        r"Chassis\s*(?:Number|No)[:\s]+([A-Z0-9]+)",
    ],
    "claim_type": [
        r"Claim\s*Type[:\s]+(.+)",
        r"Type\s+of\s+Claim[:\s]+(.+)",
        r"Nature\s+of\s+Claim[:\s]+(.+)",
        r"Peril[:\s]+(.+)",
        r"Cause\s+of\s+Loss[:\s]+(.+)",
    ],
    "attachments": [
        r"^Attachments?\s+(.+)",
        r"Documents?\s+(?:Submitted|Attached|Provided)[:\s]+(.+)",
        r"Supporting\s+Documents?[:\s]+(.+)",
        r"Evidence[:\s]+(.+)",
    ],
}

# Monetary fields need special handling
MONETARY_FIELD_PATTERNS = {
    "estimated_damage": [
        r"Estimated\s+Damage[:\s]+(.+)",
        r"Damage\s+Estimate[:\s]+(.+)",
        r"Estimated\s+(?:Repair\s+)?Cost[:\s]+(.+)",
        r"Loss\s+Amount[:\s]+(.+)",
        r"Approximate\s+(?:Loss|Damage)[:\s]+(.+)",
        r"repairs?\s+will\s+cost\s+(?:around\s+)?(.+)",
        r"narrative[^\:]*:[^\n]*?(?:INR|₹|Rs\.?)\s*([\d,]+(?:\.\d+)?(?:\s*lakh)?)",
    ],
    "initial_estimate": [
        r"Initial\s+Estimate[:\s]+(.+)",
        r"(?:Preliminary|First)\s+Estimate[:\s]+(.+)",
        r"Workshop\s+Estimate[:\s]+(.+)",
        r"Garage\s+Estimate[:\s]+(.+)",
        r"worksheet[^\:]*:[^\n]*?(?:INR|₹|Rs\.?)\s*([\d,]+(?:\.\d+)?(?:\s*lakh)?)",
        r"Approx(?:imate)?\.?\s+(?:INR|₹|Rs\.?)\s*([\d,]+)",
    ],
}


def extract_field(text: str, patterns: list) -> str | None:
    """Try each pattern in order; return first non-empty, non-placeholder match."""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            val = clean_value(m.group(1))
            val = re.split(r"\s*[\[\|]", val)[0].strip()
            val = re.sub(r"\s{2,}", " ", val)
            if not is_empty_value(val):
                return val
    return None


def extract_description_multiline(text: str) -> str | None:
    """
    Capture the full description paragraph — may span many lines.
    Stops at the next section header, MISSING note, or a known field label.
    """
    # Markers that signal end of the description block
    stop_pattern = re.compile(
        r"^\s*("
        r"[A-Z]\.\s+[A-Z]"           # section header like "C. INVOLVED"
        r"|■|n\s+MISSING"             # MISSING notes
        r"|MISSING:"
        r"|Claimant[\s:]"
        r"|Contact\s+(?:Phone|Details)"
        r"|Asset\s+Type"
        r"|Claim\s+Type"
        r"|Attachments?"
        r"|Initial\s+Estimate"
        r"|Weather"
        r")",
        re.IGNORECASE,
    )

    desc_start = re.search(
        r"(?:Description|Nature\s+of\s+(?:Loss|Damage|Incident)|What\s+Happened)"
        r"(?:\s+of\s+\w+)?\s+(.+)",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if not desc_start:
        return None

    first_line = desc_start.group(1).strip()
    # Collect continuation lines after the match
    rest = text[desc_start.end():]
    continuation_lines = []
    for line in rest.split('\n'):
        if stop_pattern.match(line):
            break
        stripped = line.strip()
        if stripped:
            continuation_lines.append(stripped)
        elif continuation_lines:
            # blank line = end of paragraph
            break

    parts = [first_line] + continuation_lines
    full = ' '.join(parts).strip()
    full = re.sub(r'\s{2,}', ' ', full)
    return full if full else None


    """Try each pattern in order; return first non-empty, non-placeholder match."""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            val = clean_value(m.group(1))
            val = re.split(r"\s*[\[\|]", val)[0].strip()
            val = re.sub(r"\s{2,}", " ", val)
            if not is_empty_value(val):
                return val
    return None


def extract_monetary(text: str, patterns: list) -> int | None:
    """
    For monetary fields: try each pattern, then parse INR from the matched text.
    Also handles DISPUTED / CONFLICTING estimates — picks the lower figure.
    """
    candidates = []
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            snippet = m.group(1)
            # Grab all amounts in the snippet
            amounts = re.findall(
                r"(?:INR|₹|Rs\.?)?\s*([\d,]+(?:\.\d+)?)\s*(?:lakh)?",
                snippet,
                re.IGNORECASE,
            )
            for a in amounts:
                parsed = parse_inr(a.strip())
                if parsed and parsed > 0:
                    candidates.append(parsed)

    if candidates:
        # Return the lowest (most conservative) when disputed
        return min(candidates)

    # Fallback: scan whole text for the field label + amount nearby
    for pat in patterns:
        label_match = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if label_match:
            # Take 200 chars after the match to find an amount
            snippet = text[label_match.start():label_match.start() + 200]
            val = parse_inr(snippet)
            if val:
                return val

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_fields(text: str) -> dict:
    data = {}

    # Standard fields
    for field, patterns in FIELD_PATTERNS.items():
        val = extract_field(text, patterns)
        if val:
            data[field] = val

    # Monetary fields
    for field, patterns in MONETARY_FIELD_PATTERNS.items():
        val = extract_monetary(text, patterns)
        if val is not None:
            data[field] = val

    # Multi-line description
    desc = extract_description_multiline(text)
    if desc:
        data["description"] = desc

    # Special: attachments — NONE SUBMITTED is a valid value, not missing
    att = _extract_attachments_raw(text)
    if att:
        data["attachments"] = att
    elif "attachments" not in data:
        pass  # stays absent → will appear in missing_fields

    # Special: effective_dates — combine Policy Effective Date + Policy Expiry Date
    if "effective_dates" not in data:
        eff = extract_field(text, [r"Policy\s*Effective\s*Date[:\s]+(.+)"])
        exp = extract_field(text, [r"Policy\s*Expiry\s*Date[:\s]+(.+)"])
        if eff and exp:
            data["effective_dates"] = f"{eff} – {exp}"
        elif eff:
            data["effective_dates"] = eff

    return data


def find_missing_fields(data: dict) -> list:
    missing = []
    for field in MANDATORY_FIELDS:
        val = data.get(field)
        if val is None or (isinstance(val, str) and is_empty_value(val)):
            missing.append(field)
    return missing


def _extract_attachments_raw(text: str) -> str | None:
    """Special handler: attachments may be NONE SUBMITTED which is a valid (present) value."""
    m = re.search(r"^Attachments?\s+(.+)", text, re.IGNORECASE | re.MULTILINE)
    if m:
        val = m.group(1).strip()
        # Strip bracketed trailing notes
        val = re.split(r"\s*—\s*claimant", val, flags=re.IGNORECASE)[0].strip()
        val = re.split(r"\s*\[", val)[0].strip()
        if val:
            return val
    return None


def find_inconsistencies(data: dict) -> list:
    inconsistencies = []

    # Damage vs estimate gap
    if "estimated_damage" in data and "initial_estimate" in data:
        diff = abs(data["estimated_damage"] - data["initial_estimate"])
        if diff > 40_000:
            inconsistencies.append(
                f"Estimated damage differs significantly from initial estimate "
                f"(gap: ₹{diff:,})"
            )

    # Redacted contact
    contact = data.get("contact_details", "")
    if contact and REDACTED_PATTERN.search(contact):
        inconsistencies.append(
            "Contact details appear partially redacted or incomplete"
        )

    # Placeholder still present after extraction (shouldn't happen but guard)
    for field in ["estimated_damage", "initial_estimate"]:
        val = data.get(field)
        if isinstance(val, str) and ("disputed" in val.lower() or "contested" in val.lower()):
            inconsistencies.append(
                f"{field.replace('_', ' ').title()} is disputed and unverified"
            )

    return inconsistencies