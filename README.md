This condensed version retains the technical architecture, core logic, and deployment steps while stripping away the granular field-by-field lists. It’s now optimized for a quick scan by developers or for a GitHub landing page.

---

## 🚀 Smart Claims Engine

**Autonomous FNOL Processing Agent**
An intelligent system that extracts data from ACORD PDFs/text, detects inconsistencies, and auto-routes insurance claims.

* **Live Demo:** [Frontend](https://smart-claims-engine.netlify.app) | [API](https://smart-claims-engine-2.onrender.com)

---

## 🏗️ Architecture & Pipeline

The system uses a **FastAPI** backend and **React (Vite)** frontend to process documents through a 5-stage pipeline:

1. **Parser (`parser.py`):** Resolves PDF fields using a 3-tier strategy (Named IDs → Tooltips → Spatial Proximity).
2. **Extractor (`extractor.py`):** A 6-pass engine combining form-data mapping, regex (`re`) patterns, and multiline narrative extraction.
3. **Config (`config.py`):** Centralized logic for data normalization, validation, and ₹INR/Lakh currency parsing.
4. **Router (`router.py`):** A strict priority engine that assigns claims to queues (Fast-track, Manual Review, Investigation, or Specialist).
5. **API (`app.py`):** Orchestrates the flow and returns structured JSON to the UI.

---

## 🚦 Routing Logic (Priority Order)

| Priority | Condition | Route |
| --- | --- | --- |
| **1. Fast-Track** | Damage < ₹25,000 + No missing fields | **Auto-Approval** |
| **2. Review** | Any mandatory fields are missing | **Manual Queue** |
| **3. Fraud** | Keywords (fraud, staged, etc.) in description | **Investigation** |
| **4. Injury** | Claim type includes "injury" or "casualty" | **Specialist** |
| **Default** | High damage value (> ₹25,000) | **Manual Review** |

---

## 🛠️ Tech Stack

* **Backend:** FastAPI, Uvicorn, Pypdf, Pdfplumber.
* **Frontend:** React, Vite, CSS3.
* **Deployment:** Render (Backend), Netlify (Frontend).

---

## 💻 Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload

```

### 2. Frontend

```bash
cd frontend-ui
npm install
npm run dev

```

### 3. API Test

```bash
curl -X POST http://localhost:8000/process-claim -F "file=@claim.pdf"

```

---

## 📂 Project Structure

* `backend/lib/`: Core logic (Parser, Extractor, Router).
* `backend/app.py`: FastAPI entry point.
* `frontend-ui/src/`: React application.
* `public/samples/`: Test PDFs for each routing outcome.