# Autonomous Insurance Claims Processing Agent

An intelligent FNOL (First Notice of Loss) document processing system that extracts key fields, detects missing or inconsistent data, and automatically routes claims to the correct workflow.

## Live Demo

- Frontend: https://smart-claims-engine.netlify.app
- Backend API: https://smart-claims-engine-2.onrender.com

---

## Approach

The system is built as a **FastAPI backend + React frontend** pipeline with four stages:

### 1. Document Parsing (`parser.py`)
Uses **pdfplumber** to extract raw text from uploaded PDF or TXT files. pdfplumber preserves layout and handles multi-column table-style FNOL documents reliably compared to basic PDF readers.

### 2. Field Extraction (`extractor.py`)
Uses **regex pattern matching** against the extracted text to locate and pull out all mandatory FNOL fields across five categories:
- Policy Information (policy number, policyholder name, effective dates)
- Incident Information (date, time, location, description)
- Involved Parties (claimant, third parties, contact details)
- Asset Details (asset type, asset ID, estimated damage)
- Other Mandatory Fields (claim type, attachments, initial estimate)

Monetary fields (`estimated_damage`, `initial_estimate`) are parsed with INR/lakh-aware logic. Placeholder values like `[Not Provided]`, `N/A`, `TBD` are treated as missing.

### 3. Inconsistency Detection (`extractor.py`)
Flags issues such as:
- Large gap between estimated damage and initial estimate (> ₹40,000)
- Partially redacted contact details

### 4. Routing (`router.py`)
Applies the four routing rules **in strict priority order**:

| Priority | Condition | Route |
|----------|-----------|-------|
| 1 | Estimated damage < ₹25,000 | Fast-track |
| 2 | Fraud keywords in description (`fraud`, `inconsistent`, `staged`) | Investigation Flag |
| 3 | Any mandatory field missing | Manual Review |
| 4 | Claim type contains `injury` | Specialist Queue |
| — | Otherwise | Standard Review |

### 5. Frontend (`app.jsx`)
A **React + Vite** interface that allows file upload or one-click sample FNOL testing. Results are displayed with extracted fields grouped by category, missing fields highlighted, inconsistencies flagged, and the full JSON API response shown.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI |
| ASGI Server | Uvicorn |
| PDF Parsing | pdfplumber |
| Field Extraction | Python `re` (regex) |
| File Uploads | python-multipart |
| Frontend | React + Vite |
| Styling | Inline CSS (no external UI lib) |

---

## Project Structure

```
claims-agent/
├── main.py              # FastAPI app, /process-claim endpoint
├── parser.py            # PDF + TXT text extraction
├── extractor.py         # Field extraction, missing fields, inconsistencies
├── router.py            # Claim routing logic
├── requirements.txt     # Python dependencies
├── uploads/             # Temp storage for uploaded files
└── frontend/
    ├── src/
    │   └── app.jsx      # React UI
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
git clone https://github.com/your-username/claims-agent.git
cd claims-agent
```

---

### 2. Install Python dependencies

```bash
pip install fastapi uvicorn pdfplumber python-multipart pydantic
```

Or using the requirements file:

```bash
pip install -r requirements.txt
```

**`requirements.txt`**
```
fastapi
uvicorn
pdfplumber
python-multipart
pydantic
```

---

### 3. Start the FastAPI backend

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

You can explore the auto-generated docs at `http://localhost:8000/docs`.

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
├── FNOL_FastTrack_ArjunMehta.pdf
├── FNOL_InvestigationFlag_MichaelDSouza.pdf
├── FNOL_SpecialistQueue_RajeshKumar.pdf
└── FNOL_ManualReview_PriyaNair.pdf
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
  -F "file=@FNOL_FastTrack_ArjunMehta.pdf"
```

---

## Sample FNOL Documents

Four sample PDFs are included, each designed to trigger a specific routing outcome:

| File | Claimant | Expected Route | Trigger |
|------|----------|----------------|---------|
| `FNOL_FastTrack_ArjunMehta.pdf` | Arjun Mehta | Fast-track | Damage = ₹18,000 (< ₹25,000), all fields present |
| `FNOL_InvestigationFlag_MichaelDSouza.pdf` | Michael D'Souza | Investigation Flag | Keywords: *staged*, *inconsistent*, *fraud* in description |
| `FNOL_SpecialistQueue_RajeshKumar.pdf` | Rajesh Kumar | Specialist Queue | Claim type = Personal Injury, all fields present |
| `FNOL_ManualReview_PriyaNair.pdf` | Priya Nair | Manual Review | Missing: effective dates, asset type, initial estimate |

---

## API Response Format

```json
{
  "extractedFields": {
    "policy_number": "POL-TN-2025-00101",
    "policyholder_name": "Arjun Mehta",
    "effective_dates": "01 January 2025 – 31 December 2025",
    "incident_date": "10 May 2026",
    "incident_time": "10:30 AM",
    "location": "Velachery Main Road, Chennai, Tamil Nadu",
    "claimant": "Arjun Mehta",
    "contact_details": "9876543210",
    "asset_type": "Private Car",
    "asset_id": "TN09AZ4321",
    "estimated_damage": 18000,
    "claim_type": "Vehicle Damage",
    "attachments": "4 Accident Scene Photographs, Workshop Quotation, RC Book copy",
    "initial_estimate": 15000
  },
  "missingFields": [],
  "inconsistencies": [],
  "recommendedRoute": "Fast-track",
  "reasoning": "Estimated damage is below ₹25,000"
}
```

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