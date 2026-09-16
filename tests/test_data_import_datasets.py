"""Events and Requisitions intake, alongside daily operations.

One workbook can carry all three. Each sheet is recognised by its own columns,
versioned under its own business key, and merged into the dataset the rest of
the product already reads -- events into banquets, requisitions into
submissions.
"""

from __future__ import annotations

from pathlib import Path

from ui.backend import data_import_service as service
from ui.backend import repository as repo

TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "ui" / "frontend" / "public" / "samples"
    / "dineastra_daily_operations_template.xlsx"
)


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


def test_each_kind_of_file_is_recognised_by_its_own_columns():
    events = service.parse_upload("events.csv", _events_csv())
    requisitions = service.parse_upload("reqs.csv", _requisitions_csv())

    assert list(events.tables) == ["events"]
    assert list(requisitions.tables) == ["requisitions"]


def test_the_template_workbook_carries_all_three_sheets():
    parsed = service.parse_upload(TEMPLATE.name, TEMPLATE.read_bytes())

    assert set(parsed.tables) == {"daily", "events", "requisitions"}
    assert parsed.rejects == []
    assert parsed.accepted == sum(len(rows) for rows in parsed.tables.values())


def test_a_sheet_the_importer_does_not_know_is_skipped_not_refused(tmp_path):
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

    path = tmp_path / "mixed.xlsx"
    workbook.save(path)
    parsed = service.parse_upload("mixed.xlsx", path.read_bytes())

    assert list(parsed.tables) == ["events"]


# ------------------------------------------------------------------ figures


def test_event_margin_is_computed_not_read_from_the_sheet():
    record = service.parse_upload("events.csv", _events_csv()).tables["events"][0]

    # 800000 - (180000 + 50000 + 90000 + 30000) = 450000, so 56.25%
    assert record["net"] == 450000
    assert record["margin_pct"] == 56.2
    assert "margin" not in _events_csv().decode().split("\n")[0]


def test_requisition_total_is_computed():
    record = service.parse_upload("reqs.csv", _requisitions_csv()).tables["requisitions"][0]
    assert record["total_cost"] == 3600.0


def test_an_unknown_event_segment_is_rejected():
    """Each segment has its own margin floor, so an unknown one has none."""
    bad = _events_csv().replace(b"corporate", b"banquet-ish")
    parsed = service.parse_upload("events.csv", bad)

    assert parsed.tables["events"] == []
    assert "segment must be one of" in parsed.rejects[0]["reason"]


# ------------------------------------------------------- versioning and merge


def test_each_dataset_versions_under_its_own_key():
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


def test_an_uploaded_event_joins_the_banquet_dataset():
    seeded_count = len(repo.banquets_all())
    service.ingest(service.parse_upload("e.csv", _events_csv()).tables, "e.csv", "owner@example.com")

    merged = repo.banquets_all()
    assert len(merged) == seeded_count + 1
    added = next(event for event in merged if event["id"] == "BQ-2026-501")
    assert added["margin_pct"] == 56.2
    assert added["source"] == "Data Studio"


def test_an_uploaded_requisition_joins_the_submissions_dataset():
    seeded_count = len(repo.submissions_all())
    service.ingest(
        service.parse_upload("r.csv", _requisitions_csv()).tables, "r.csv", "owner@example.com"
    )

    merged = repo.submissions_all()
    assert len(merged) == seeded_count + 1
    assert repo.submission_by_id("SUB-009001")["total_cost"] == 3600.0


def test_an_upload_can_correct_a_seeded_event():
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


def test_reset_clears_every_dataset():
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


def test_status_reports_each_dataset_after_a_mixed_upload():
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


def test_the_built_in_sample_loads_through_the_ordinary_import_path():
    """The "Load sample data" button must exercise the real importer.

    If the sample and the importer ever drift apart, this fails here rather
    than in front of whoever clicked the button.
    """
    from ui.backend import sample_upload

    result = sample_upload.load("owner@example.com")

    assert result["created"] == 12
    assert set(result["datasets"]) == {"daily", "events", "requisitions"}
    assert result["datasets"]["daily"]["processed"] == 6
    # and it is idempotent, like any other upload
    again = sample_upload.load("owner@example.com")
    assert again["unchanged"] == 12 and again["created"] == 0


def test_the_button_and_the_downloadable_file_are_the_same_rows():
    """Load the sample, then upload the template: nothing should look changed.

    These were two copies of the same rows and drifted apart in their note
    text, so the demo reported edits where none had been made.
    """
    from ui.backend import sample_upload

    sample_upload.load("owner@example.com")
    parsed = service.parse_upload(TEMPLATE.name, TEMPLATE.read_bytes())
    result = service.ingest(parsed.tables, TEMPLATE.name, "owner@example.com")

    assert result["created"] == 0
    assert result["updated"] == 0
    assert result["unchanged"] == 12
