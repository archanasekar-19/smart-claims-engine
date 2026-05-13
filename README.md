# Smart Claims Engine — Autonomous Insurance Claims Processing Agent

An intelligent FNOL (First Notice of Loss) document processing system that extracts key fields from fillable ACORD PDFs and narrative text documents, detects missing or inconsistent data, and automatically routes claims to the correct workflow queue.

## Live Demo

- **Frontend:** [smart-claims-engine.netlify.app](https://smart-claims-engine.netlify.app)
- **Backend API:** [smart-claims-engine-2.onrender.com](https://smart-claims-engine-2.onrender.com)

---

## Architecture Overview

The system is a **FastAPI backend + React (Vite) frontend** pipeline with five sequential stages:

```
Upload (PDF / TXT)
        │
        ▼
  [parser.py]  ──────────── 3-tier field resolution ────────────
        │                                                       │
        ▼                                                       │
 [extractor.py] ── form fields + TEXT_PATTERNS + fallbacks ────┘
        │
        ▼
 [config.py]  ── missing-field detection + inconsistency checks
        │
        ▼
 [router.py]  ── 4-rule priority routing engine
        │
        ▼
  JSON response  ──→  React UI
```

---

## Module Logic (Deep Dive)

### `backend/lib/parser.py` — Document Parsing & Field Resolution

Handles two document types and resolves form fields using a **three-tier strategy**:

#### Tier 0 — Named field IDs (ACORD standard labels)
Named ACORD fields (e.g. `"PLATE NUMBER"`, `"VIN"`, `"DESCRIBE DAMAGE"`) are their own label. These are mapped directly via `_NAMED_FIELD_MAP` to internal keys with no spatial work required.

#### Tier 1 — `/TU` tooltip metadata
PDF form fields carry an optional `/TU` (tooltip) attribute set by the form author. When present, this is the authoritative human-readable label (e.g. `"POLICY NUMBER"`, `"DATE OF BIRTH"`). Resolved first before any spatial analysis.

#### Tier 2 — Spatial proximity (same-row or directly above)
Fields with no tooltip (unnamed fields like `Text7`, `Text8`, `Text45`) are resolved by finding the printed text on the page closest to the field's bounding box:
- **Same-row:** words on the same horizontal line whose right edge is within 180px to the left of the field.
- **Above:** words whose bottom edge is within 22px above the field top, horizontally within 200px of the field centre.

This maps, for example, `Text8 → "LINE OF BUSINESS"` and `Text45 → "ESTIMATE AMOUNT"` automatically.

#### Tier 3 — Header-band x-position + value shape
The ACORD 2 form's top header band has tightly packed fields (date-of-loss, time, claim number) that share a single printed label. Spatial proximity is ambiguous here. Resolution uses the field's horizontal x-centre combined with value shape:
- Value matches `dd/mm/yyyy` → `incident_date`
- Value matches `HH:MM` → `incident_time`
- Alphanumeric code at left/mid of band → `claim_number`

**TXT fallback:** When no fillable form fields are found, the file is read as plain text and returned with an empty `form_fields` dict for regex-based extraction.

`parser.extract()` returns:
```python
{
  "text":        str,   # raw full text (used by router for keyword scan)
  "form_fields": dict,  # internal_key → value (populated for fillable PDFs)
  "is_form":     bool,  # True when AcroForm fields were found and filled
}
```

---

### `backend/lib/config.py` — Field Mappings, Patterns & Utilities

Central configuration file. Defines all constants and helper functions used across the pipeline.

#### `MANDATORY_FIELDS`
List of 15 fields that must be present for a claim to be considered complete:
`policy_number`, `policyholder_name`, `effective_dates`, `incident_date`, `incident_time`, `location`, `description`, `claimant`, `contact_details`, `asset_type`, `asset_id`, `estimated_damage`, `claim_type`, `attachments`, `initial_estimate`.

#### `ACORD_FIELD_MAP`
Maps ACORD form label strings → internal snake_case keys. Only named/labelled fields (not positional `Text*` fields) are listed here. Used by `extractor.py` step 2a.

#### `TEXT_PATTERNS` & `MONEY_PATTERNS`
Regex pattern banks for each extractable field. Tried in order; first match wins. Covers:
- Policy info (`policy_number`, `policyholder_name`, `effective_dates`)
- Incident info (`incident_date`, `incident_time`, `location`)
- Parties (`claimant`, `contact_details`)
- Asset info (`asset_type`, `asset_id`)
- Monetary values (`estimated_damage`, `initial_estimate`) with INR/lakh/`₹`/`$` parsing

#### Key Utility Functions

| Function | Purpose |
|----------|---------|
| `is_empty(v)` | Returns `True` for `None`, blank strings, placeholder text (`[not provided]`, `N/A`, `TBD`, `--`), and fully-redacted strings (all X's) |
| `clean(v)` | Strips leading/trailing whitespace |
| `normalize(s)` | Uppercases and collapses internal whitespace to single spaces |
| `parse_money(s)` | Extracts numeric amount from strings like `"₹18,000"`, `"INR 45000"`, `"2.5 lakh"` |
| `match_field(text, patterns)` | Tries each regex in the list; returns first non-empty, non-junk match |
| `match_money(text, patterns)` | Like `match_field` but coerces result to integer via `parse_money` |
| `extract_multiline_description(text)` | Walks forward line-by-line from a description header, collecting lines until a section-stop pattern is encountered |
| `find_missing_fields(extracted)` | Checks each mandatory field via `is_empty`; returns list of missing field names |
| `find_inconsistencies(extracted)` | Checks: incident date after report date (high severity), claimant differs from policyholder by character-set similarity < 0.7 (medium), negative or >₹10M damage amount, missing contact details |
| `similarity_score(s1, s2)` | Character-set Jaccard similarity (0–1) used by inconsistency checker |

---

### `backend/lib/extractor.py` — Multi-Pass Field Extraction Engine

Orchestrates extraction in six sequential steps, each filling gaps left by the previous step.

**Step 1 — Parse the file**
Calls `parser.extract()` to get `form_fields` and `text`.

**Step 2a — Map named ACORD field IDs**
Iterates `ACORD_FIELD_MAP`; maps each ACORD label to its internal key. Skips empty/placeholder values.

**Step 2b — Merge spatially resolved internal keys**
Fields already resolved by the parser's spatial tiers (e.g. `policy_number`, `estimated_damage`) are merged in directly without re-mapping.

**Step 2c — Coerce monetary fields**
Runs `parse_money()` on `estimated_damage` and `initial_estimate` to produce integers rather than raw strings.

**Step 2d — Validate `incident_time`**
Rejects times with impossible hour (>23) or minute (>59) values — catches parser misreads like `"38:20"`.

**Step 2e — Composite location**
If `location` is missing, builds it from `location_street + location_city`.

**Step 2f — Promote `asset_id`**
If `asset_id` is missing, promotes `plate_number` first, then `vin`.

**Step 3 — TEXT_PATTERNS**
For each field still missing after form extraction, runs `match_field()` against the full raw text using `TEXT_PATTERNS`. Includes a second `incident_time` validation pass to reject bad values introduced by regex.

**Step 4 — MONEY_PATTERNS**
Fills monetary fields still missing using `match_money()` against full text.

**Step 5 — Multi-line description**
If `description` is still missing, calls `extract_multiline_description()` to recover narrative text by walking forward past a description header until a section stop.

**Step 6 — Fallback strategies (`_apply_fallbacks`)**
Last-resort per-field fallbacks:
- **`contact_details`:** Assembles from `contact_phone` + `contact_email` form fields (pipe-separated). Falls back to scanning text for phone/email patterns.
- **`policy_number`:** Tries additional regex patterns, minimum 6-character requirement.
- **`effective_dates`:** Scans for `"Policy Period: D/M/YYYY to D/M/YYYY"` in raw text.
- **`incident_date`:** Explicit date-labeled patterns only (avoids matching addresses). Last resort: raw `Text1` form field if it matches `dd/mm/yyyy`.
- **`incident_time`:** Broad time patterns, only if still missing.
- **`claim_type`:** Additional patterns, then `Text8` form field directly, then infers from `asset_type` keyword matching (`"hatchback"` → `"Motor Vehicle Damage"`).
- **`attachments`:** Scans REMARKS field for `"Attachments: ..."` sub-line or `"Photographs attached..."` pattern.

---

### `backend/lib/router.py` — Priority Routing Engine

Applies **four rules in strict priority order**. The first rule to fire wins; lower-priority rules are never evaluated.

| Priority | Condition | Route | Reasoning Generated |
|----------|-----------|-------|---------------------|
| 1 | `estimated_damage` > 0 and < ₹25,000 | **Fast-track** | Names claimant, date, location, confirms no flags |
| 2 | Any field in `_ROUTING_MANDATORY` is missing | **Manual Review** | Lists each missing field by human-readable label |
| 3 | `description` field (not raw text) contains `fraud`, `inconsistent`, `staged`, `planned`, `fake`, or `intentional` | **Investigation Flag** | Lists triggered keywords, names SIU escalation |
| 4 | `claim_type` contains `injury`, `bodily injury`, `personal injury`, or `casualty` | **Specialist Queue** | Explains injury specialist requirements |
| — | Otherwise (high damage, no flags) | **Manual Review** | States damage threshold exceeded or estimate absent |

> **Why description-only for fraud scanning?** ACORD forms pages 3–4 contain state anti-fraud legal notices that include the word "fraudulent" — scanning raw text would flag every single claim as fraudulent.

`_to_number(value)` handles lakh strings (`"2.5 lakh"` → `250000`), comma-formatted numbers, and raw int/float values uniformly.

---

### `backend/app.py` — FastAPI Application

Single endpoint: `POST /process-claim`

1. Saves the uploaded file to the `uploads/` directory
2. Runs `extract_claim()` → `extracted_fields`
3. Runs `find_missing_fields()` → `missing_fields`
4. Runs `find_inconsistencies()` → `inconsistencies`
5. Re-calls `extract()` to get raw text for router keyword scope
6. Runs `route_claim()` → `(recommended_route, reasoning)`
7. Deletes the uploaded file
8. Returns JSON response

Also exposes `GET /health` for deployment health checks.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI + Uvicorn |
| Fillable PDF parsing | pypdf (AcroForm / `/Rect` annotations) |
| Spatial label resolution | pdfplumber (word bounding boxes) |
| Field Extraction | Direct field-ID mapping + `re` regex fallbacks |
| File Uploads | python-multipart |
| Frontend | React + Vite |
| Styling | Inline CSS (no external UI library) |

---

## Project Structure

```
smart-claims-engine/
├── backend/
│   ├── app.py                  # FastAPI app, /process-claim endpoint
│   ├── requirements.txt
│   ├── render.yaml             # Render deployment config
│   ├── uploads/                # Temp storage (auto-cleaned after each request)
│   └── lib/
│       ├── config.py           # Field maps, regex patterns, utility functions
│       ├── parser.py           # PDF/TXT parsing — 3-tier field resolution
│       ├── extractor.py        # 6-step extraction pipeline + fallbacks
│       └── router.py           # 4-rule priority routing engine
└── frontend-ui/
    ├── src/
    │   └── App.jsx             # React UI — upload, processing animation, results
    ├── public/
    │   └── samples/            # Sample FNOL PDFs served statically
    ├── index.html
    └── package.json
```

---

## Steps to Run

### Prerequisites
- Python 3.9+
- Node.js 18+

### 1. Clone the repository

```bash
git clone https://github.com/archanasekar-19/smart-claims-engine.git
cd smart-claims-engine
```

### 2. Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

**`requirements.txt`**
```
fastapi
uvicorn
pypdf
pdfplumber
python-multipart
pydantic
```

### 3. Start the FastAPI backend

```bash
uvicorn app:app --reload --port 8000
```

API available at `http://localhost:8000`  
Swagger docs: `http://localhost:8000/docs`

### 4. Install and start the frontend

```bash
cd frontend-ui
npm install
```

Create `.env` inside `frontend-ui/`:
```env
VITE_API_URL=http://localhost:8000
```

```bash
npm run dev
```

Frontend available at `http://localhost:5173`

### 5. Test the API directly (optional)

```bash
curl -X POST http://localhost:8000/process-claim \
  -F "file=@backend/uploads/FNOL_T1_FastTrack.pdf"
```

---

## Sample FNOL Documents

Four ACORD Automobile Loss Notice PDFs (ACORD 2), each engineered to trigger exactly one routing outcome:

| File | Claimant | Expected Route | Trigger |
|------|----------|----------------|---------|
| `ROUTE1_FastTrack.pdf` | Aditya Ramesh Kumar | **Fast-track** | Damage = ₹18,000 (< ₹25,000 threshold), all fields present, no fraud words |
| `ROUTE2_ManualReview.pdf` | Meena Subramaniam | **Manual Review** | Missing: incident time, contact details, asset type, effective dates, initial estimate |
| `ROUTE3_InvestigationFlag.pdf` | Vikram Anand Shetty | **Investigation Flag** | Description contains *staged*, *inconsistent*, *fraud*; all fields present, damage > ₹25,000 |
| `ROUTE4_SpecialistQueue.pdf` | Preethi Lakshmi Narayan | **Specialist Queue** | Line of Business = `Injury`; all fields present, no fraud words, damage > ₹25,000 |

---

## API Response Format

`POST /process-claim` → JSON:

```json
{
  "extractedFields": {
    "policyholder_name": "Aditya Ramesh Kumar",
    "policy_number": "SAFE-2024-AUTO-10045",
    "incident_date": "05/10/2026",
    "incident_time": "10:30 AM",
    "location": "Velachery Main Road, Near SRM Flyover, Chennai, TN 600042",
    "description": "Insured vehicle was stationary at a red light when a two-wheeler collided with the rear bumper at low speed. Minor paint scrape and a small dent.",
    "claimant": "Aditya Ramesh Kumar",
    "contact_details": "9840012345",
    "asset_type": "Hatchback",
    "asset_id": "TN09BZ4421",
    "estimated_damage": 18000,
    "claim_type": "Personal Auto",
    "attachments": "See damage description",
    "vehicle_make": "Maruti Suzuki",
    "vehicle_year": "2023",
    "carrier": "SafeGuard General Insurance"
  },
  "missingFields": ["effective_dates", "initial_estimate"],
  "inconsistencies": [],
  "recommendedRoute": "Fast-track",
  "reasoning": "Estimated damage of ₹18,000 is below the ₹25,000 fast-track threshold. The claim filed by Aditya Ramesh Kumar on 05/10/2026 at Velachery Main Road has all mandatory fields present, contains no fraud indicators, and does not involve personal injury. This claim qualifies for accelerated straight-through processing with no manual intervention required."
}
```

---

## Routing Logic Summary

```
Damage < ₹25,000?
  └─ YES → Fast-track
     NO ↓
Any mandatory field missing?
  └─ YES → Manual Review
     NO ↓
"fraud" / "staged" / "inconsistent" in description?
  └─ YES → Investigation Flag
     NO ↓
Claim type contains "injury"?
  └─ YES → Specialist Queue
     NO ↓
           → Manual Review (high damage / no estimate)
```

---

## Deployment

### Backend — Render

| Field | Value |
|-------|-------|
| Service | Web Service |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app:app --host 0.0.0.0 --port $PORT` |
| Live URL | https://smart-claims-engine-2.onrender.com |

### Frontend — Netlify

| Field | Value |
|-------|-------|
| Base Directory | `frontend-ui` |
| Build Command | `npm run build` |
| Publish Directory | `dist` |
| Environment Variable | `VITE_API_URL=https://smart-claims-engine-2.onrender.com` |
| Live URL | https://smart-claims-engine.netlify.app |