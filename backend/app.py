from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from parser import extract_text
from extractor import (
    extract_fields,
    find_missing_fields,
    find_inconsistencies
)
from router import route_claim
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

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    text = extract_text(file_path)

    extracted_fields = extract_fields(text)

    missing_fields = find_missing_fields(extracted_fields)

    inconsistencies = find_inconsistencies(extracted_fields)

    recommended_route, reasoning = route_claim(
        extracted_fields,
        missing_fields,
        inconsistencies,
        text
    )

    return {
        "extractedFields": extracted_fields,
        "missingFields": missing_fields,
        "inconsistencies": inconsistencies,
        "recommendedRoute": recommended_route,
        "reasoning": reasoning
    }