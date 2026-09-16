"""Data access for the DineAstra demo.

Every read of data/ goes through this module. Routes and the metric registry
never open a file themselves. Files are loaded once and cached in memory;
the dataset is static and regenerated offline by scripts/seed_data.py.

ANCHOR_DATE is the simulated "today" for the demo and matches the constant in
scripts/seed_data.py. It is deliberately not date.today().
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
DOCS_DIR = DATA_DIR / "docs"
RUNTIME_DIR = DATA_DIR / "runtime"

ANCHOR_DATE = date(2026, 9, 14)

# Uploaded documents live only for the lifetime of the process, per spec:
# an upload is searchable "in the same session".
_SESSION_DOCUMENTS: dict[str, dict] = {}


class DataMissingError(RuntimeError):
    """Raised when data/ has not been seeded yet."""


@lru_cache(maxsize=None)
def _load_json(name: str):
    path = DATA_DIR / name
    if not path.exists():
        raise DataMissingError(
            f"data/{name} is missing. Run: python scripts/seed_data.py"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def parse_date(value: str | date | None, default: date | None = None) -> date:
    """Parse an ISO date, falling back to ANCHOR_DATE."""
    if value is None or value == "":
        return default or ANCHOR_DATE
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def anchor_date() -> date:
    """The simulated "today", always the fixed ANCHOR_DATE.

    Uploaded rows dated after the seeded window are still merged, reachable
    through the date selector and counted in trailing windows -- but they do
    not move "today". Every figure the demo is built around is anchored to one
    business date, and a single late upload would otherwise silently restate
    all of them.
    """
    return ANCHOR_DATE


# ---------------------------------------------------------------------------
# daily property
# ---------------------------------------------------------------------------


def daily_property_all() -> list[dict]:
    """The seeded days, with any accepted upload laid over the matching date.

    An upload restates the trade of the outlets it covers. It is overlaid
    rather than swapped in wholesale so that facts about the estate rather
    than the day -- the seat count the per-seat figures divide by -- survive.
    """
    seeded = list(_load_json("daily_property.json"))
    from ui.backend import data_import_service

    imported = data_import_service.current_daily_rows()
    if not imported:
        return seeded
    by_date = {row["date"]: row for row in seeded}
    for row in imported:
        by_date[row["date"]] = data_import_service.overlay_daily_row(
            by_date.get(row["date"]), row
        )
    return [by_date[key] for key in sorted(by_date)]


def daily_property_for(day: str | date) -> dict | None:
    target = parse_date(day).isoformat()
    for row in daily_property_all():
        if row["date"] == target:
            return row
    return None


def daily_property_range(end: str | date, days: int) -> list[dict]:
    """The `days` rows ending on `end` inclusive, oldest first."""
    end_date = parse_date(end)
    start_date = end_date - timedelta(days=days - 1)
    start_iso, end_iso = start_date.isoformat(), end_date.isoformat()
    return [r for r in daily_property_all() if start_iso <= r["date"] <= end_iso]


def daily_property_trailing(end: str | date, days: int, offset: int = 1) -> list[dict]:
    """The `days` rows ending `offset` days before `end` -- the comparison
    baseline for a given day, excluding the day itself by default."""
    end_date = parse_date(end) - timedelta(days=offset)
    return daily_property_range(end_date, days)


def property_date_bounds() -> tuple[str, str]:
    rows = daily_property_all()
    return rows[0]["date"], rows[-1]["date"]


# ---------------------------------------------------------------------------
# banquets
# ---------------------------------------------------------------------------


def _merge_by_id(seeded: list[dict], imported: list[dict], source: str) -> list[dict]:
    """Seeded rows with any uploaded row of the same id laid over them.

    An event or a requisition line is a self-contained record, so an upload
    replaces the whole row rather than patching fields into it -- unlike a
    business day, where the estate facts have to be carried across.
    """
    if not imported:
        return seeded
    by_id = {row["id"]: row for row in seeded}
    for row in imported:
        by_id[row["id"]] = {**row, "source": source}
    return sorted(by_id.values(), key=lambda row: (row["date"], row["id"]))


def banquets_all() -> list[dict]:
    from ui.backend import data_import_service

    return _merge_by_id(
        list(_load_json("banquets.json")),
        data_import_service.current_events(),
        "Data Studio",
    )


def banquet_by_id(event_id: str) -> dict | None:
    for event in banquets_all():
        if event["id"] == event_id:
            return event
    return None


def banquets_by_segment(segment: str) -> list[dict]:
    return [e for e in banquets_all() if e["segment"] == segment]


def banquet_peers(event: dict) -> list[dict]:
    """Same-segment events excluding the event itself."""
    return [
        e
        for e in banquets_by_segment(event["segment"])
        if e["id"] != event["id"]
    ]


def banquets_for_date(day: str | date) -> list[dict]:
    target = parse_date(day).isoformat()
    return [e for e in banquets_all() if e["date"] == target]


# ---------------------------------------------------------------------------
# submissions
# ---------------------------------------------------------------------------


def submissions_all() -> list[dict]:
    from ui.backend import data_import_service

    return _merge_by_id(
        list(_load_json("submissions.json")),
        data_import_service.current_requisitions(),
        "Data Studio",
    )


def submissions_for_date(day: str | date) -> list[dict]:
    target = parse_date(day).isoformat()
    return [s for s in submissions_all() if s["date"] == target]


def submission_by_id(submission_id: str) -> dict | None:
    for row in submissions_all():
        if row["id"] == submission_id:
            return row
    return None


def submissions_date_bounds() -> tuple[str, str]:
    rows = submissions_all()
    dates = sorted({r["date"] for r in rows})
    return dates[0], dates[-1]


# ---------------------------------------------------------------------------
# connections / users
# ---------------------------------------------------------------------------


def connections_all() -> list[dict]:
    return _load_json("connections.json")


def user_by_email(email: str) -> dict | None:
    for user in _load_json("users.json"):
        if user["email"].lower() == email.lower().strip():
            return user
    return None


# ---------------------------------------------------------------------------
# documents
# ---------------------------------------------------------------------------


def documents_meta() -> list[dict]:
    """Seeded documents plus anything uploaded during this process's life."""
    return list(_load_json("documents_meta.json")) + [
        {k: v for k, v in doc.items() if k != "text"}
        for doc in _SESSION_DOCUMENTS.values()
    ]


def document_meta(doc_id: str) -> dict | None:
    for meta in documents_meta():
        if meta["id"] == doc_id:
            return meta
    return None


def document_text(doc_id: str) -> str | None:
    if doc_id in _SESSION_DOCUMENTS:
        return _SESSION_DOCUMENTS[doc_id]["text"]
    meta = document_meta(doc_id)
    if meta is None:
        return None
    path = DOCS_DIR / meta["filename"]
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def documents_with_text() -> list[dict]:
    out = []
    for meta in documents_meta():
        text = document_text(meta["id"])
        if text is not None:
            out.append({**meta, "text": text})
    return out


def add_session_document(doc_id: str, title: str, filename: str, text: str) -> dict:
    """Register an uploaded document for the lifetime of this process."""
    meta = {
        "id": doc_id,
        "title": title,
        "filename": filename,
        "department": "Uploaded",
        "last_verified": None,
        "uploaded": True,
        "word_count": len(text.split()),
    }
    _SESSION_DOCUMENTS[doc_id] = {**meta, "text": text}
    return meta
