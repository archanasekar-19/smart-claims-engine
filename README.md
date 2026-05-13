# Autonomous Insurance Claims Processing Agent

An intelligent FNOL (First Notice of Loss) document processing system that extracts key fields, detects missing or inconsistent data, and automatically routes claims to the correct workflow.

## Live Demo

- Frontend: <a href="https://smart-claims-engine.netlify.app" target="_blank">smart-claims-engine.netlify.app</a>
- Backend API: <a href="https://smart-claims-engine-2.onrender.com" target="_blank">smart-claims-engine-2.onrender.com</a>

---

## Approach

The system is built as a **FastAPI backend + React frontend** pipeline with five stages:

### 1. Document Parsing (`parser.py`)

Handles two document types with different strategies:

**Fillable PDFs (e.g. ACORD forms)**
Uses **pypdf** to call `get_fields()` and read form field values directly from the PDF's AcroForm layer. This bypasses text extraction entirely — field values are read from the PDF data structure, not from rendered text. This eliminates misreads caused by form labels bleeding into extracted text.

**Plain-text PDFs and TXT files**
Falls back to **pdfplumber** text extraction when no fillable form fields are detected. This handles narrative FNOL documents, scanned text, and `.txt` uploads.

`parser.extract()` returns a dict:
```python
{
  "text":        str,   # raw text (used by router for keyword scan)
  "form_fields": dict,  # field_id -> value (populated for fillable PDFs)
  "is_form":     bool,  # True when AcroForm fields were found and filled
}
```

### 2. Field Extraction (`extractor.py`)

Automatically selects extraction mode based on the parsed document type:

**Form mode (`extract_from_acord_form`)**
Maps ACORD form field IDs directly to our standard field keys using a hardcoded lookup table (`_ACORD` dict). No regex. Example mappings:
- `"DESCRIPTION OF ACCIDENT ACORD 101..."` → `description`
- `"Text45"` → `estimate_raw` (Estimate Amount field)
- `"Text7"` → `claim_type` (Line of Business field)
- `"TYPE BODY"` → `asset_type`
- `"PLATE NUMBER"` / `"VIN"` → `asset_id`
- `"PHONE  CELL HOME BUS PRIMARY"` → `contact_details`

**Text mode (`extract_from_text`)**
Uses regex pattern matching against extracted text for narrative PDFs and TXT files. Extracts fields across five categories:
- Policy Information (policy number, policyholder name, effective dates)
- Incident Information (date, time, location, description)
- Involved Parties (claimant, third parties, contact details)
- Asset Details (asset type, asset ID, estimated damage)
- Other Mandatory Fields (claim type, attachments, initial estimate)

Monetary fields are parsed with `$`, `INR`, `₹`, and lakh-aware logic. Placeholder values like `[Not Provided]`, `N/A`, `TBD`, fully-redacted strings (`98XXX XXXXX`) are treated as missing.

Multi-line description fields are captured by walking forward line-by-line until a section header or known field label is encountered.

### 3. Inconsistency Detection (`extractor.py`)

Flags issues such as:
- Large gap between `estimated_damage` and `initial_estimate` (> ₹40,000)
- Partially redacted contact details (detected via `XXX` pattern)

### 4. Routing (`router.py`)

Applies four routing rules in **strict priority order**. The description field value (not raw PDF text) is scanned for fraud keywords — this prevents false positives from boilerplate legal text present on pages 3–4 of ACORD forms.

| Priority | Condition | Route |
|----------|-----------|-------|
| 1 | Estimated damage > 0 and < ₹25,000 | Fast-track |
| 2 | Any mandatory field is missing | Manual Review |
| 3 | Description contains `fraud`, `inconsistent`, or `staged` | Investigation Flag |
| 4 | Claim type (Line of Business) = `Injury` | Specialist Queue |
| — | Otherwise | Standard Review |

Routing reasoning is dynamically generated using extracted field values (claimant name, date, location, damage amount, missing field list, triggered keywords) to produce a detailed, context-specific explanation.

### 5. Frontend (`App.jsx`)

A **React + Vite** interface with:
- File upload (drag & drop or Browse Files)
- One-click sample FNOL PDF testing with colour-coded route badges and PDF download buttons
- 2-second animated processing sequence (step indicators, dual-ring spinner)
- Results display: routing decision, reasoning, missing fields, inconsistency warnings
- Extracted fields grouped by category in a label-row layout
- Full API response shown as formatted JSON

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI |
| ASGI Server | Uvicorn |
| Fillable PDF parsing | pypdf (`get_fields()`) |
| Narrative PDF parsing | pdfplumber |
| Field Extraction | Direct field-ID mapping (form) / Python `re` (text) |
| File Uploads | python-multipart |
| Frontend | React + Vite |
| Styling | Inline CSS (no external UI library) |

---

## Project Structure

```
claims-agent/
├── app.py               # FastAPI app, /process-claim endpoint
├── parser.py            # PDF + TXT parsing (pypdf for forms, pdfplumber for text)
├── extractor.py         # Field extraction, missing fields, inconsistencies
├── router.py            # Claim routing logic (strict priority order)
├── requirements.txt     # Python dependencies
├── uploads/             # Temp storage for uploaded files
└── frontend/
    ├── src/
    │   └── App.jsx      # React UI
    ├── public/
    │   └── samples/     # Sample FNOL PDFs served statically
    └── package.json
```

---

## Steps to Run

### Prerequisites
- Python 3.9+
- Node.js 18+
- pip

---

### 1. Clone the repository

```bash
git clone https://github.com/archanasekar-19/smart-claims-engine.git
cd smart-claims-engine
```

---

### 2. Install Python dependencies

```bash
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

---

### 3. Start the FastAPI backend

```bash
uvicorn app:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

Auto-generated docs: `http://localhost:8000/docs`

---

### 4. Install frontend dependencies

```bash
cd frontend
npm install
```

---

### 5. Configure the API URL

Create a `.env` file inside the `frontend/` folder:

```env
VITE_API_URL=http://localhost:8000
```

---

### 6. Add sample FNOL PDFs

Copy the four generated sample PDFs into `frontend/public/samples/`:

```
frontend/public/samples/
├── ROUTE1_FastTrack.pdf
├── ROUTE2_ManualReview.pdf
├── ROUTE3_InvestigationFlag.pdf
└── ROUTE4_SpecialistQueue.pdf
```

---

### 7. Start the frontend

```bash
npm run dev
```

The app will be available at `http://localhost:5173`.

---

### 8. Test the API directly (optional)

```bash
curl -X POST http://localhost:8000/process-claim \
  -F "file=@ROUTE1_FastTrack.pdf"
```

---

## Sample FNOL Documents

Four ACORD Automobile Loss Notice PDFs (ACORD 2, 2016/10), each filled to trigger exactly one routing outcome:

| File | Claimant | Expected Route | Trigger |
|------|----------|----------------|---------|
| `ROUTE1_FastTrack.pdf` | Aditya Ramesh Kumar | Fast-track | Damage = ₹18,000 (< ₹25,000), all fields present, no fraud words |
| `ROUTE2_ManualReview.pdf` | Meena Subramaniam | Manual Review | Missing: incident time, contact details, asset type, effective dates, initial estimate |
| `ROUTE3_InvestigationFlag.pdf` | Vikram Anand Shetty | Investigation Flag | Description contains *staged*, *inconsistent*, *fraud*; all fields present, damage > ₹25,000 |
| `ROUTE4_SpecialistQueue.pdf` | Preethi Lakshmi Narayan | Specialist Queue | Line of Business = `Injury`; all fields present, no fraud words, damage > ₹25,000 |

Each PDF is engineered so only its intended priority rule fires and all higher-priority rules are explicitly blocked.

---

## API Response Format

```json
{
  "extractedFields": {
    "policyholder_name": "Aditya Ramesh Kumar",
    "incident_date": "05/10/2026",
    "incident_time": "10:30 AM",
    "location": "Velachery Main Road, Near SRM Flyover, Chennai, Tamil Nadu 600042, India",
    "description": "Insured vehicle was stationary at a red light when a two-wheeler collided with the rear bumper at low speed. Minor paint scrape and a small dent on the rear bumper. No injuries sustained.",
    "claimant": "Aditya Ramesh Kumar",
    "contact_details": "9840012345",
    "asset_type": "Hatchback",
    "asset_id": "TN09BZ4421",
    "estimated_damage": 18000,
    "claim_type": "Personal Auto",
    "attachments": "See damage description",
    "vehicle_make": "Maruti Suzuki",
    "vehicle_year": "2023",
    "carrier": "SafeGuard General Insurance",
    "date_filed": "05/10/2026"
  },
  "missingFields": ["policy_number", "effective_dates", "initial_estimate"],
  "inconsistencies": [],
  "recommendedRoute": "Fast-track",
  "reasoning": "Estimated damage of ₹18,000 is below the ₹25,000 fast-track threshold. The claim filed by Aditya Ramesh Kumar on 05/10/2026 at Velachery Main Road, Near SRM Flyover, Chennai, Tamil Nadu 600042, India has all mandatory fields present, contains no fraud indicators, and does not involve personal injury. This claim qualifies for accelerated straight-through processing with no manual intervention required."
}
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
| Base Directory | `frontend` |
| Build Command | `npm run build` |
| Publish Directory | `dist` |
| Environment Variable | `VITE_API_URL=https://smart-claims-engine-2.onrender.com` |
| Live URL | https://smart-claims-engine.netlify.app |