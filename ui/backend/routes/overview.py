"""Overview read routes. Handlers stay thin: all derivation is in analysis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ui.backend import analysis, auth
from ui.backend import repository as repo

router = APIRouter(prefix="/api", tags=["overview"])


@router.get("/overview")
def get_overview(
    date: str | None = Query(default=None, description="ISO date; defaults to the demo's today"),
    user: dict = Depends(auth.current_user),
) -> dict:
    day = repo.parse_date(date).isoformat()
    return analysis.overview(day)


@router.get("/overview/digest")
def get_digest(
    date: str | None = Query(default=None),
    user: dict = Depends(auth.current_user),
) -> dict:
    day = repo.parse_date(date).isoformat()
    return analysis.whatsapp_digest(day)
