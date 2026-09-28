import os
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from pypdf import PdfReader

from dependencies import get_current_agent
from ingest_docs import run_ingestion

router = APIRouter()

BLACKBOARD_DOCS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "blackboard_docs")
)


@router.post("/admin/upload-doc")
async def upload_doc(
    file: UploadFile = File(...),
    agent_id: int = Depends(get_current_agent),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Read the uploaded PDF into memory and extract its text
    contents = await file.read()
    tmp_path = os.path.join(BLACKBOARD_DOCS_DIR, file.filename)

    with open(tmp_path, "wb") as f:
        f.write(contents)

    try:
        reader = PdfReader(tmp_path)
        extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        os.remove(tmp_path)
        raise HTTPException(status_code=400, detail=f"Failed to read PDF: {str(e)}")

    # Remove the raw PDF and save the extracted text instead, since
    # run_ingestion() only reads .txt / .md files from blackboard_docs/
    os.remove(tmp_path)
    txt_filename = os.path.splitext(file.filename)[0] + ".txt"
    txt_path = os.path.join(BLACKBOARD_DOCS_DIR, txt_filename)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(extracted_text)

    # Re-run the full ingestion pipeline so the new doc gets embedded
    result = run_ingestion()

    return {
        "filename": txt_filename,
        "ingestion_result": result,
    }