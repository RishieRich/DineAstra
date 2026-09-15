"""Operations read routes: requisitions and the computed contrast pair."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ui.backend import analysis, auth
from ui.backend import repository as repo

router = APIRouter(prefix="/api/operations", tags=["operations"])


@router.get("/submissions")
def get_submissions(
    date: str | None = Query(default=None),
    user: dict = Depends(auth.current_user),
) -> dict:
    day = repo.parse_date(date).isoformat()
    return analysis.submissions_view(day)
