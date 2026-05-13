Here is your **ready-to-use `README.md` file**:

````markdown
# 🚀 Smart Claims Engine

**Autonomous FNOL Processing Agent**  
An intelligent system that extracts structured data from insurance FNOL PDFs/text, detects inconsistencies, and automatically routes claims to the correct workflow.

**Live Demo:**  
Frontend → https://smart-claims-engine.netlify.app  
Backend API → https://smart-claims-engine-2.onrender.com  

---

## 🏗️ Architecture & Pipeline

The system is built using a **FastAPI backend** and **React (Vite) frontend**, following a structured 5-stage processing pipeline:

### 1. Parser (`parser.py`)
Extracts raw text from PDFs/TXT using `pdfplumber`, preserving layout and handling multi-column FNOL documents.

### 2. Extractor (`extractor.py`)
A multi-pass extraction engine that combines:
- Regex-based field extraction (`re`)
- Multiline narrative parsing
- INR/Lakh-aware monetary normalization
- Missing-value detection (`N/A`, `TBD`, `[Not Provided]`)

### 3. Config (`config.py`)
Centralized validation and normalization layer for consistent field formatting and currency parsing.

### 4. Routing Engine (`router.py`)
Applies strict priority-based routing rules to classify claims into appropriate workflows.

### 5. API Layer (`main.py` / `app.py`)
Orchestrates the full pipeline and returns structured JSON responses to the frontend.

---

## 🚦 Routing Logic (Priority Order)

| Priority | Condition | Route |
|----------|-----------|------|
| 1 | Damage < ₹25,000 AND no missing fields | **Fast-track (Auto Approval)** |
| 2 | Any mandatory fields missing | **Manual Review** |
| 3 | Fraud indicators (fraud, staged, inconsistent) | **Investigation Flag** |
| 4 | Claim type includes injury/casualty | **Specialist Queue** |
| — | Otherwise | **Standard Review** |

---

## 🛠️ Tech Stack

- **Backend:** FastAPI, Uvicorn, pdfplumber  
- **Frontend:** React + Vite  
- **Parsing:** pdfplumber  
- **Extraction:** Python Regex (`re`)  
- **Deployment:** Render (API), Netlify (UI)

---

## 💻 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/archanasekar-19/smart-claims-engine.git
cd smart-claims-engine
````

---

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

API runs at:

```
http://localhost:8000
```

API Docs:

```
http://localhost:8000/docs
```

---

### 3. Frontend Setup

```bash
cd frontend-ui
npm install
npm run dev
```

Frontend runs at:

```
http://localhost:5173
```

---

### 4. Environment Variables

Create `.env` inside `frontend-ui/`:

```env
VITE_API_URL=http://localhost:8000
```

---

### 5. Test API (CLI)

```bash
curl -X POST http://localhost:8000/process-claim \
-F "file=@claim.pdf"
```

---

## 📂 Project Structure

```
backend/
├── app.py              # FastAPI entry point
├── parser.py          # PDF/TXT text extraction
├── extractor.py       # Field extraction + validation
├── router.py          # Routing logic engine
├── config.py          # Normalization & rules
├── uploads/           # Temporary file storage

frontend-ui/
├── src/
│   └── app.jsx        # Main React UI
├── public/
│   └── samples/       # Sample FNOL PDFs
└── package.json
```

---

## 📄 Sample FNOL Scenarios

| File              | Expected Route   | Trigger                            |
| ----------------- | ---------------- | ---------------------------------- |
| FastTrack.pdf     | Fast-track       | Low damage (< ₹25K), complete data |
| Investigation.pdf | Investigation    | Fraud keywords detected            |
| Specialist.pdf    | Specialist Queue | Injury/casualty claim              |
| ManualReview.pdf  | Manual Review    | Missing mandatory fields           |

---

## 📌 Key Features

* Automated FNOL document parsing
* Structured field extraction from PDFs
* Missing data detection
* Fraud/inconsistency flagging
* Priority-based claim routing engine
* React-based interactive dashboard
* JSON API-ready output

---

## 🚀 Deployment

### Backend (Render)

* Root: `backend`
* Start: `uvicorn app:app --host 0.0.0.0 --port $PORT`

### Frontend (Netlify)

* Base: `frontend-ui`
* Build: `npm run build`
* Publish: `dist`

---

```