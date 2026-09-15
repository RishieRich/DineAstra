"""Data Studio routes for files and quick daily entry."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from ui.backend import auth, data_import_service

router = APIRouter(prefix="/api/data", tags=["data"])


class QuickEntry(BaseModel):
    date: str
    outlet: str = Field(min_length=1)
    net_sales: float = Field(ge=0)
    covers: int = Field(ge=0)
    food_cost_pct: float = Field(ge=0, le=100)
    labour_cost_pct: float = Field(ge=0, le=100)
    checklist_total: int = Field(ge=0)
    checklist_signed_off: int = Field(ge=0)
    notes: str = ""


@router.get("/status")
def import_status(user: dict = Depends(auth.current_user)) -> dict:
    return data_import_service.status_payload()


@router.post("/upload")
async def upload_data(
    file: UploadFile = File(...),
    user: dict = Depends(auth.current_user),
) -> dict:
    content = await file.read()
    try:
        rows = data_import_service.parse_upload(file.filename, content)
        result = data_import_service.ingest(rows, file.filename or "upload", user["email"])
    except data_import_service.DataImportError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {**result, "data_status": data_import_service.status_payload()}


@router.post("/quick-entry")
def quick_entry(
    payload: QuickEntry,
    user: dict = Depends(auth.current_user),
) -> dict:
    try:
        result = data_import_service.ingest_quick_entry(
            payload.model_dump(), user["email"]
        )
    except data_import_service.DataImportError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {**result, "data_status": data_import_service.status_payload()}
