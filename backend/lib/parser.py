"""
parser.py — reads PDF or TXT and extracts:
- form fields (ACORD fillable PDFs)
- full text (narrative or fallback OCR-ready text source)
"""

import os


def extract(file_path: str) -> dict:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return _read_pdf(file_path)

    return _read_txt(file_path)


def extract_text(file_path: str) -> str:
    """Backward compatibility"""
    return extract(file_path)["text"]


# ============================================================
# PDF READER (FIXED)
# ============================================================

def _read_pdf(path: str) -> dict:
    from pypdf import PdfReader

    reader = PdfReader(path)

    form_fields = {}

    raw_fields = reader.get_fields() or {}

    for name, obj in raw_fields.items():
        value = ""

        if isinstance(obj, dict):
            value = obj.get("/V", "") or obj.get("/DV", "") or ""

        if isinstance(value, str) and value.startswith("/"):
            value = value[1:]

        form_fields[name] = str(value).strip()

    # ALSO capture annotation fallback (IMPORTANT FIX)
    try:
        for page in reader.pages:
            if "/Annots" in page:
                for annot in page["/Annots"]:
                    try:
                        obj = annot.get_object()
                        if "/T" in obj and "/V" in obj:
                            form_fields[obj["/T"]] = str(obj["/V"])
                    except:
                        pass
    except:
        pass

    # Extract text from pages
    pages_text = []
    for p in reader.pages:
        pages_text.append(p.extract_text() or "")

    text = "\n".join(pages_text)

    # If form exists, enrich text with key-value dump
    if any(form_fields.values()):
        kv = "\n".join(f"{k}: {v}" for k, v in form_fields.items() if v)
        text = kv + "\n\n" + text

    return {
        "text": text,
        "form_fields": form_fields,
        "is_form": bool(form_fields),
    }


# ============================================================
# TXT READER
# ============================================================

def _read_txt(path: str) -> dict:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    return {
        "text": text,
        "form_fields": {},
        "is_form": False,
    }