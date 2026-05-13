"""
parser.py — reads PDF or TXT, returns form_fields (internal_key → value) + text.

FIELD RESOLUTION STRATEGY (three tiers, applied in order):

  1. /TU tooltip metadata
     PDF form fields carry an optional /TU (tooltip) attribute set by the
     form author — a human-readable label like "POLICY NUMBER" or
     "DATE OF BIRTH". When present, this is the authoritative label.
     Named field_ids (e.g. "PLATE NUMBER") double as their own label.

  2. Spatial proximity — same-row or directly above
     Fields with no tooltip (e.g. Text7, Text8, Text45) are resolved by
     finding the printed text on the page closest to the field box, searching
     first on the same horizontal row (label to the left), then directly above.
     This works perfectly for standalone labelled fields like:
       Text7  → "POLICY NUMBER"   (label directly above)
       Text8  → "LINE OF BUSINESS" (label directly above)
       Text45 → "ESTIMATE AMOUNT" (label to the left on same row)

  3. Header-band x-position
     Some fields sit in the dense top header band of the ACORD form where
     multiple fields share a single multi-word header label. Here spatial
     proximity returns an ambiguous phrase like "DATE OF LOSS AND TIME".
     We resolve these by the field's horizontal x-centre within the band —
     each slot in the header occupies a known x-range that maps to a
     specific semantic meaning (date-of-loss, time, claim-number, etc.).
"""

import os
import re

try:
    import pdfplumber
    _HAS_PDFPLUMBER = True
except ImportError:
    _HAS_PDFPLUMBER = False


# ── Label → internal key ────────────────────────────────────────────────────
# Printed label text (lowercased, punctuation stripped) → internal field name.
# Substring match; longest match wins.

_LABEL_TO_KEY = {
    "policy number":     "policy_number",
    "line of business":  "claim_type",
    "estimate amount":   "estimated_damage",
    "estimate":          "estimated_damage",
    "date of loss":      "incident_date",
    "time of loss":      "incident_time",
    "time":              "incident_time",
    "date":              "incident_date",
    "claim":             "claim_number",
    "file":              "claim_number",
    "agency":            "agency_name",
    "when to contact":   "when_to_contact",
}

# Named field_id → internal key (field_id IS the label for these)
_NAMED_FIELD_MAP = {
    "POLICY NUMBER":              "policy_number",
    "CARRIER":                    "carrier",
    "NAIC CODE":                  "naic_code",
    "NAME OF INSURED First Middle Last": "policyholder_name",
    "INSUREDS MAILING ADDRESS":   "insured_address",
    "DATE OF BIRTH":              "insured_dob",
    "PHONE  CELL HOME BUS PRIMARY": "contact_phone",
    "PRIMARY EMAIL ADDRESS":      "contact_email",
    "NAME OF CONTACT First Middle Last": "claimant",
    "STREET LOCATION OF LOSS":    "location_street",
    "CITY STATE ZIP":             "location_city",
    "COUNTRY":                    "location_country",
    "POLICE OR FIRE DEPARTMENT CONTACTED": "police_contacted",
    "REPORT NUMBER":              "report_number",
    "DESCRIPTION OF ACCIDENT ACORD 101 Additional Remarks Schedule may be attached if more space is required": "description",
    "VEH":          "veh_num",
    "YEAR":         "vehicle_year",
    "MAKE":         "vehicle_make",
    "TYPE BODY":    "asset_type",
    "MODEL":        "vehicle_model",
    "VIN":          "vin",
    "PLATE NUMBER": "plate_number",
    "STATE":        "vehicle_state",
    "Employee family etc RELATION TO INSURED": "relation_to_insured",
    "DRIVERS LICENSE NUMBER":     "driver_license",
    "PURPOSE OF USE":             "purpose_of_use",
    "DESCRIBE DAMAGE":            "describe_damage",
    "WHERE CAN VEHICLE BE SEEN":  "where_vehicle_seen",
    "WHEN CAN VEHICLE BE SEEN":   "when_vehicle_seen",
    "OTHER INSURANCE ON VEHICLE  CARRIER": "other_ins_carrier",
    "REMARKS ACORD 101 Additional Remarks Schedule may be attached if more space is required": "remarks",
}

_UNLABELLED = re.compile(r"^(Text|Check\s*Box|Row)\d+$", re.I)


def _normalise(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().rstrip(":").strip()).lower()


def _label_to_internal(label: str) -> str | None:
    """Match a label string to an internal key (longest substring match)."""
    norm = _normalise(label)
    best_key, best_len = None, 0
    for lk, ik in _LABEL_TO_KEY.items():
        if lk in norm and len(lk) > best_len:
            best_key, best_len = ik, len(lk)
    return best_key


def _find_label_spatially(words, fx0, fx1, f_top, f_bottom):
    """
    Find the printed label for a field using spatial proximity.

    Strategy:
      1. Same-row: words on the same horizontal line whose right edge is
         within 180px to the LEFT of the field's left edge.
      2. Above: words whose bottom is within 22px directly above the field's
         top, horizontally overlapping or close (within 200px of field centre).

    Returns the joined text of the best candidate cluster.
    """
    f_cx = (fx0 + fx1) / 2
    f_cy = (f_top + f_bottom) / 2

    same_row, above_row = [], []
    for w in words:
        w_cx = (w["x0"] + w["x1"]) / 2
        w_cy = (w["top"] + w["bottom"]) / 2

        if abs(w_cy - f_cy) < 8 and w["x1"] < fx0 and (fx0 - w["x1"]) < 180:
            same_row.append(w)
        elif w["bottom"] <= f_top + 4 and w["bottom"] >= f_top - 22:
            if abs(w_cx - f_cx) < 200:
                above_row.append(w)

    candidates = same_row if same_row else above_row
    if not candidates:
        return ""
    candidates.sort(key=lambda w: w["x0"])
    return " ".join(w["text"] for w in candidates)


def _resolve_header_band_field(fx0, fx1, fval):
    """
    Tier 3: resolve fields packed in the dense ACORD top-header band.

    In the ACORD 2 form, the top ~80pt contains a row of tightly packed
    fields (date-of-loss, time, claim number) that share a single printed
    header label. Spatial proximity returns an ambiguous phrase for all of
    them. We resolve using the field's x-centre position within the page,
    combined with value shape (date vs time vs alphanumeric).

    The ACORD 2 header band runs across the full page width (~612pt).
    Observed x-ranges (from annotation /Rect inspection):
      x 300-450 = claim/file number field
      x 450-530 = date of loss field
      x 520-570 = time of loss field

    We also validate the value shape to avoid misassignment:
      date  pattern: dd/mm/yyyy
      time  pattern: HH:MM
    """
    f_cx = (fx0 + fx1) / 2

    is_date = bool(re.match(r"\d{1,2}/\d{1,2}/\d{4}$", fval.strip()))
    is_time = bool(re.match(r"\d{1,2}:\d{2}$", fval.strip()))

    if is_date:
        return "incident_date"
    if is_time:
        return "incident_time"
    # alphanumeric code at left/mid of header band → claim number
    if f_cx < 500:
        return "claim_number"
    return None


def _read_pdf(path: str) -> dict:
    from pypdf import PdfReader
    reader = PdfReader(path)

    # ── collect annotation metadata: field_id → {value, page_idx, rect, tooltip}
    field_meta = {}
    for page_idx, page in enumerate(reader.pages):
        for annot_ref in page.get("/Annots", []):
            try:
                obj = annot_ref.get_object()
                fid = obj.get("/T", "")
                if not fid:
                    continue
                raw_v   = obj.get("/V", "") or obj.get("/DV", "") or ""
                value   = str(raw_v).lstrip("/").strip()
                tooltip = str(obj.get("/TU", "") or "").strip()
                rect    = obj.get("/Rect", None)
                field_meta[fid] = {
                    "value":   value,
                    "tooltip": tooltip,
                    "page_idx": page_idx,
                    "rect":    [float(x) for x in rect] if rect else None,
                }
            except Exception:
                pass

    # ── resolve unlabelled fields via spatial proximity ──────────────────
    spatial_labels = {}   # field_id → resolved label string

    if _HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(path) as pdf:
                for page_idx, plumb_page in enumerate(pdf.pages):
                    ph = plumb_page.height
                    words = plumb_page.extract_words(keep_blank_chars=False)

                    for fid, meta in field_meta.items():
                        if meta["page_idx"] != page_idx:
                            continue
                        if not _UNLABELLED.match(fid):
                            continue
                        if meta["tooltip"]:          # tier 1 already available
                            continue
                        if not meta["value"] or meta["value"] in ("Off", ""):
                            continue
                        if not meta["rect"]:
                            continue

                        x0, y0_pdf, x1, y1_pdf = meta["rect"]
                        f_top    = ph - y1_pdf
                        f_bottom = ph - y0_pdf

                        label = _find_label_spatially(words, x0, x1, f_top, f_bottom)
                        spatial_labels[fid] = label
        except Exception:
            pass

    # ── build form_fields dict ───────────────────────────────────────────
    form_fields = {}

    for fid, meta in field_meta.items():
        value = meta["value"]
        if not value or value in ("Off", ""):
            continue

        # ── Tier 0: named field_id is its own label ──────────────────────
        if fid in _NAMED_FIELD_MAP:
            key = _NAMED_FIELD_MAP[fid]
            if key not in form_fields:
                form_fields[key] = value
            continue

        if not _UNLABELLED.match(fid):
            continue   # non-standard field_id with no known mapping — skip

        # ── Tier 1: /TU tooltip ──────────────────────────────────────────
        if meta["tooltip"]:
            key = _label_to_internal(meta["tooltip"])
            if key and key not in form_fields:
                form_fields[key] = value
            continue

        # ── Tier 2: spatial proximity ────────────────────────────────────
        label_raw = spatial_labels.get(fid, "")
        if label_raw:
            key = _label_to_internal(label_raw)
            if key and key not in form_fields:
                form_fields[key] = value
                continue

        # ── Tier 3: header-band x-position + value shape ────────────────
        if meta["rect"]:
            x0, _, x1, _ = meta["rect"]
            key = _resolve_header_band_field(x0, x1, value)
            if key and key not in form_fields:
                form_fields[key] = value

    # ── full text extraction ─────────────────────────────────────────────
    pages_text = [p.extract_text() or "" for p in reader.pages]
    text = "\n".join(pages_text)
    if form_fields:
        kv = "\n".join(f"{k}: {v}" for k, v in form_fields.items() if v)
        text = kv + "\n\n" + text

    return {"text": text, "form_fields": form_fields, "is_form": bool(form_fields)}


def _read_txt(path: str) -> dict:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    return {"text": text, "form_fields": {}, "is_form": False}


def extract(file_path: str) -> dict:
    ext = os.path.splitext(file_path)[1].lower()
    return _read_pdf(file_path) if ext == ".pdf" else _read_txt(file_path)


def extract_text(file_path: str) -> str:
    return extract(file_path)["text"]