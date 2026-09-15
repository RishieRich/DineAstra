"""Property Brain routes: documents, document-scoped questions, checklist
generation, and upload.

Handlers stay thin; the work is in agents/ and ui/backend/brain_service.py.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from ui.backend import auth, brain_service

router = APIRouter(prefix="/api/brain", tags=["brain"])

UPLOAD_STATUS = {
    "too_large": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    "unsupported_type": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    "not_utf8": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
}


class BrainQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    document_id: str | None = None


class ChecklistRequest(BaseModel):
    document_id: str
    section: str | None = None


@router.get("/documents")
def list_documents(user: dict = Depends(auth.current_user)) -> dict:
    return brain_service.documents()


@router.get("/documents/{doc_id}")
def get_document(doc_id: str, user: dict = Depends(auth.current_user)) -> dict:
    document = brain_service.document(doc_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=brain_service.DOCUMENT_NOT_FOUND,
        )
    return document


@router.post("/ask")
def ask_document(
    payload: BrainQuestion, user: dict = Depends(auth.current_user)
) -> dict:
    return brain_service.answer(payload.question, payload.document_id)


@router.post("/generate-checklist")
def generate_checklist(
    payload: ChecklistRequest, user: dict = Depends(auth.current_user)
) -> dict:
    result = brain_service.checklist(payload.document_id, payload.section)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=brain_service.NO_CHECKLIST_IN_DOCUMENT,
        )
    return result


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...), user: dict = Depends(auth.current_user)
) -> dict:
    content = await file.read()
    accepted, reason, detail = brain_service.validate_upload(file.filename, content)
    if not accepted:
        raise HTTPException(status_code=UPLOAD_STATUS[reason], detail=detail)
    return brain_service.store_upload(file.filename, content)
