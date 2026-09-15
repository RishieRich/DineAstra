"""Banquet read routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ui.backend import analysis, auth
from ui.backend import repository as repo

router = APIRouter(prefix="/api/banquet", tags=["banquet"])

EVENT_NOT_FOUND = "No banquet event with that reference."


@router.get("/events")
def list_events(
    segment: str | None = Query(default=None),
    user: dict = Depends(auth.current_user),
) -> dict:
    return analysis.banquet_list(segment)


@router.get("/events/{event_id}")
def get_event(
    event_id: str,
    user: dict = Depends(auth.current_user),
) -> dict:
    event = repo.banquet_by_id(event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=EVENT_NOT_FOUND
        )
    return analysis.banquet_detail(event)
