from fastapi import FastAPI
from pydantic import BaseModel
from .ai import extract_crm_fields
from .crm import push_to_crm

app = FastAPI()

class NotesIn(BaseModel):
    notes: str

@app.post("/upload-notes")
def upload_notes(data: NotesIn):
    extracted = extract_crm_fields(data.notes)
    crm_response = push_to_crm(extracted)

    return {
        "review_summary": extracted["summary"],
        "extracted_fields": extracted,
        "crm_status": crm_response
    }
