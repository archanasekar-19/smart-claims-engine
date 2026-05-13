from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from lib.parser import extract
from lib.extractor import extract_claim
from lib.config import find_missing_fields, find_inconsistencies
from lib.router import route_claim
import shutil
import os

app = FastAPI(title="Autonomous Insurance Claims Processing Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/process-claim")
async def process_claim(file: UploadFile = File(...)):
    """
    Process an insurance claim document (PDF or TXT).
    Extracts fields, identifies missing data, detects inconsistencies, and recommends routing.
    """
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # extract_claim() handles full extraction pipeline
    extracted_fields = extract_claim(file_path)

    # Find missing critical fields
    missing_fields = find_missing_fields(extracted_fields)

    # Detect data inconsistencies
    inconsistencies = find_inconsistencies(extracted_fields)

    # Get raw text for keyword scanning in router
    parsed = extract(file_path)
    text = parsed.get("text", "")

    # Route the claim based on extracted data
    recommended_route, reasoning = route_claim(
        extracted_fields,
        missing_fields,
        inconsistencies,
        text,
    )

    # Cleanup uploaded file
    try:
        os.remove(file_path)
    except:
        pass

    return {
        "extractedFields": extracted_fields,
        "missingFields": missing_fields,
        "inconsistencies": inconsistencies,
        "recommendedRoute": recommended_route,
        "reasoning": reasoning,
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
