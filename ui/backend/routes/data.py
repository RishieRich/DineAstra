"""Data Studio routes for files and quick daily entry."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from ui.backend import auth, data_import_service
from ui.backend import repository as repo

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
    payload = data_import_service.status_payload()
    first, last = repo.property_date_bounds()
    return {
        **payload,
        # "today" is the demo's fixed business date. The range can extend past
        # it once data is uploaded for later days, so the two are not the same
        # question and the dashboard needs both.
        "today": repo.anchor_date().isoformat(),
        "available_date_range": {"first": first, "last": last},
        "last_updated_at": payload["recent_batches"][0]["loaded_at"]
        if payload["recent_batches"]
        else None,
    }


@router.post("/upload")
async def upload_data(
    file: UploadFile = File(...),
    user: dict = Depends(auth.current_user),
) -> dict:
    content = await file.read()
    source = file.filename or "upload"
    try:
        parsed = data_import_service.parse_upload(file.filename, content)
        result = data_import_service.ingest(parsed.tables, source, user["email"])
    except data_import_service.DataImportError as exc:
        # Only a problem with the file itself reaches here. A problem with a
        # row is reported as a reject, not as a failed upload.
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    data_import_service.store_reject_report(result["batch_id"], parsed.rejects)
    return {
        **result,
        "rejected": len(parsed.rejects),
        # Enough to show the reader what went wrong without making them
        # download anything; the full list is in the report.
        "rejects": parsed.rejects[:10],
        "reject_report_url": (
            f"/api/data/rejects/{result['batch_id']}" if parsed.rejects else None
        ),
        "data_status": data_import_service.status_payload(),
    }


@router.get("/rejects/{batch_id}", response_class=PlainTextResponse)
def reject_report(
    batch_id: str,
    user: dict = Depends(auth.current_user),
) -> PlainTextResponse:
    """The rejected rows of one batch, as a CSV to correct and re-upload."""
    report = data_import_service.load_reject_report(batch_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No reject report exists for that upload.",
        )
    return PlainTextResponse(
        content=report,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{batch_id}-rejected-rows.csv"'
        },
    )


class ResetRequest(BaseModel):
    confirmation: str = Field(
        description="Must be the exact confirmation phrase; the reset is not undoable."
    )


@router.post("/reset")
def reset_uploads(
    payload: ResetRequest,
    user: dict = Depends(auth.current_user),
) -> dict:
    """Discard every uploaded record and go back to the seeded sample data."""
    try:
        result = data_import_service.reset_to_sample(payload.confirmation)
    except data_import_service.DataImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
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
