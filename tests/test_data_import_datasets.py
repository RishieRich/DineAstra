"""Events and Requisitions intake, alongside daily operations.

One workbook can carry all three. Each sheet is recognised by its own columns,
versioned under its own business key, and merged into the dataset the rest of
the product already reads -- events into banquets, requisitions into
submissions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ui.backend import data_import_service as service
from ui.backend import repository as repo

TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "ui" / "frontend" / "public" / "samples"
    / "dineastra_daily_operations_template.xlsx"
)


@pytest.fixture
def clean_history(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "HISTORY_PATH", tmp_path / "history.json")
    monkeypatch.setattr(service, "REJECT_DIR", tmp_path / "reject_reports")
    return tmp_path


def _events_csv() -> bytes:
    return (
        "event_id,event_name,segment,date,covers,venue,revenue,food_cost,"
        "beverage_cost,labour_cost,other_cost\n"
        "BQ-2026-501,Northwind Leadership Dinner,corporate,2026-09-18,48,"
        "Astra House Private Room,800000,180000,50000,90000,30000\n"
    ).encode()


def _requisitions_csv() -> bytes:
    return (
        "requisition_id,date,item,department,vendor,unit_cost,quantity\n"
        "SUB-009001,2026-09-18,Saffron 10g,Kitchen & Stewarding,Kesar House,900,4\n"
    ).encode()


# --------------------------------------------------------------- recognition


def test_each_kind_of_file_is_recognised_by_its_own_columns(clean_history):
    events = service.parse_upload("events.csv", _events_csv())
    requisitions = service.parse_upload("reqs.csv", _requisitions_csv())

    assert list(events.tables) == ["events"]
    assert list(requisitions.tables) == ["requisitions"]


def test_the_template_workbook_carries_all_three_sheets(clean_history):
    parsed = service.parse_upload(TEMPLATE.name, TEMPLATE.read_bytes())

    assert set(parsed.tables) == {"daily", "events", "requisitions"}
    assert parsed.rejects == []
    assert parsed.accepted == sum(len(rows) for rows in parsed.tables.values())


def test_a_sheet_the_importer_does_not_know_is_skipped_not_refused(clean_history):
    """A customer's own extra sheet is none of the importer's business."""
    from openpyxl import Workbook

    workbook = Workbook()
    unrelated = workbook.active
    unrelated.title = "Staff Roster"
    unrelated.append(["employee", "shift", "hours"])
    unrelated.append(["A. Rao", "Evening", 8])

    events = workbook.create_sheet("Events")
    for row in _events_csv().decode().strip().split("\n"):
        events.append(row.split(","))

    path = clean_history / "mixed.xlsx"
    workbook.save(path)
    parsed = service.parse_upload("mixed.xlsx", path.read_bytes())

    assert list(parsed.tables) == ["events"]


# ------------------------------------------------------------------ figures


def test_event_margin_is_computed_not_read_from_the_sheet(clean_history):
    record = service.parse_upload("events.csv", _events_csv()).tables["events"][0]

    # 800000 - (180000 + 50000 + 90000 + 30000) = 450000, so 56.25%
    assert record["net"] == 450000
    assert record["margin_pct"] == 56.2
    assert "margin" not in _events_csv().decode().split("\n")[0]


def test_requisition_total_is_computed(clean_history):
    record = service.parse_upload("reqs.csv", _requisitions_csv()).tables["requisitions"][0]
    assert record["total_cost"] == 3600.0


def test_an_unknown_event_segment_is_rejected(clean_history):
    """Each segment has its own margin floor, so an unknown one has none."""
    bad = _events_csv().replace(b"corporate", b"banquet-ish")
    parsed = service.parse_upload("events.csv", bad)

    assert parsed.tables["events"] == []
    assert "segment must be one of" in parsed.rejects[0]["reason"]


# ------------------------------------------------------- versioning and merge


def test_each_dataset_versions_under_its_own_key(clean_history):
    service.ingest(service.parse_upload("e.csv", _events_csv()).tables, "e.csv", "owner@example.com")
    revised = _events_csv().replace(b"800000", b"880000")
    result = service.ingest(
        service.parse_upload("e2.csv", revised).tables, "e2.csv", "owner@example.com"
    )

    assert result["updated"] == 1
    assert result["datasets"]["events"]["updated"] == 1
    history = service._read_history()
    assert [row["is_current"] for row in history] == [False, True]
    assert history[1]["dataset"] == "events"
    assert service.current_events()[0]["revenue"] == 880000


def test_an_uploaded_event_joins_the_banquet_dataset(clean_history):
    seeded_count = len(repo.banquets_all())
    service.ingest(service.parse_upload("e.csv", _events_csv()).tables, "e.csv", "owner@example.com")

    merged = repo.banquets_all()
    assert len(merged) == seeded_count + 1
    added = next(event for event in merged if event["id"] == "BQ-2026-501")
    assert added["margin_pct"] == 56.2
    assert added["source"] == "Data Studio"


def test_an_uploaded_requisition_joins_the_submissions_dataset(clean_history):
    seeded_count = len(repo.submissions_all())
    service.ingest(
        service.parse_upload("r.csv", _requisitions_csv()).tables, "r.csv", "owner@example.com"
    )

    merged = repo.submissions_all()
    assert len(merged) == seeded_count + 1
    assert repo.submission_by_id("SUB-009001")["total_cost"] == 3600.0


def test_an_upload_can_correct_a_seeded_event(clean_history):
    """Uploading an existing id replaces that event rather than duplicating it."""
    seeded = repo.banquet_by_id("BQ-2026-018")
    assert seeded is not None and seeded["margin_pct"] == 55.6

    corrected = (
        "event_id,event_name,segment,date,covers,venue,revenue,food_cost,"
        "beverage_cost,labour_cost,other_cost\n"
        # Venue names carry a comma, so the field is quoted the way a
        # spreadsheet would export it.
        f"BQ-2026-018,{seeded['name']},{seeded['segment']},{seeded['date']},"
        f"{seeded['covers']},\"{seeded['venue']}\",1000000,200000,50000,100000,50000\n"
    ).encode()
    service.ingest(
        service.parse_upload("fix.csv", corrected).tables, "fix.csv", "owner@example.com"
    )

    assert len(repo.banquets_all()) == 24
    assert repo.banquet_by_id("BQ-2026-018")["margin_pct"] == 60.0


def test_reset_clears_every_dataset(clean_history):
    service.ingest(
        service.parse_upload(TEMPLATE.name, TEMPLATE.read_bytes()).tables,
        TEMPLATE.name,
        "owner@example.com",
    )
    assert service.current_events() and service.current_requisitions()

    service.reset_to_sample("RESET")

    assert service.current_records() == []
    assert service.current_events() == []
    assert service.current_requisitions() == []
    assert len(repo.banquets_all()) == 24


def test_status_reports_each_dataset_after_a_mixed_upload(clean_history):
    """The status payload must survive rows that have no outlet column."""
    service.ingest(
        service.parse_upload(TEMPLATE.name, TEMPLATE.read_bytes()).tables,
        TEMPLATE.name,
        "owner@example.com",
    )
    status = service.status_payload()

    assert set(status["datasets"]) == {"daily", "events", "requisitions"}
    assert status["datasets"]["events"]["label"] == "Events"
    assert status["outlets"] == 3
    assert status["current_records"] == 12
    assert status["has_uploads"] is True
