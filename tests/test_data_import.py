"""Data Studio parsing and slowly-changing-dimension behaviour."""

from __future__ import annotations

from ui.backend import data_import_service as service


def _csv(sales: int = 214600) -> bytes:
    return (
        "date,outlet,dine_in_sales,delivery_sales,covers,food_cost_pct,"
        "labour_cost_pct,checklist_total,checklist_signed_off,notes\n"
        f"2026-09-16,Astra House Indiranagar,{sales},48200,182,33.9,26.4,34,33,Closing check\n"
    ).encode()


def test_csv_upload_builds_a_current_daily_record():
    rows = service.parse_upload("daily.csv", _csv()).records
    result = service.ingest(rows, "daily.csv", "owner@example.com")

    assert result["created"] == 1
    assert result["updated"] == 0
    daily = service.current_daily_rows()[0]
    assert daily["date"] == "2026-09-16"
    assert daily["dine_in_revenue"] == 214600
    assert daily["delivery_revenue"] == 48200
    assert daily["total_revenue"] == 262800
    assert daily["covers"] == 182
    assert daily["outlet_count"] == 1
    # The aggregate reports only what the upload stated. A sheet cannot know
    # how many seats were trading, so it carries no per-seat figure at all and
    # cannot pass a fabricated one downstream.
    assert "seats" not in daily
    assert "sales_per_seat" not in daily


def test_overlay_on_a_seeded_day_keeps_the_estate_facts():
    """An upload restates the day's trade; the seat count is not the day's."""
    service.ingest(service.parse_upload("daily.csv", _csv()).records, "daily.csv", "owner@example.com")
    seeded = {
        "date": "2026-09-16",
        "day_of_week": "Wednesday",
        "seats": 250,
        "covers": 470,
        "total_revenue": 724455,
        "dine_in_revenue": 551310,
    }
    row = service.overlay_daily_row(seeded, service.current_daily_rows()[0])

    # the estate fact survives, and the per-seat figures follow from it
    assert row["seats"] == 250
    assert row["sales_per_seat"] == round(214600 / 250, 2)
    assert row["table_turns"] == round(182 / 250, 2)
    # the day's trade is the uploaded day's, not the seeded day's
    assert row["covers"] == 182
    assert row["total_revenue"] == 262800


def test_overlay_without_a_seeded_day_reports_per_seat_as_unknown():
    """A brand new date has no seat count, and says so rather than showing zero."""
    service.ingest(service.parse_upload("daily.csv", _csv()).records, "daily.csv", "owner@example.com")
    row = service.overlay_daily_row(None, service.current_daily_rows()[0])

    assert row["seats"] is None
    assert row["sales_per_seat"] is None
    assert row["table_turns"] is None
    assert row["void_comp_pct"] is None
    assert row["total_revenue"] == 262800
    assert row["checklist_signoff_pct"] == 97.1


def test_changed_business_key_keeps_type_2_history():
    service.ingest(service.parse_upload("first.csv", _csv()).records, "first.csv", "owner@example.com")
    result = service.ingest(
        service.parse_upload("revision.csv", _csv(sales=228000)).records,
        "revision.csv",
        "owner@example.com",
    )

    history = service._read_history()
    assert result["updated"] == 1
    assert len(history) == 2
    assert [row["is_current"] for row in history] == [False, True]
    assert history[0]["valid_to"] == history[1]["valid_from"]
    assert history[1]["version"] == 2


def test_unchanged_upload_is_idempotent():
    rows = service.parse_upload("daily.csv", _csv()).records
    service.ingest(rows, "daily.csv", "owner@example.com")
    result = service.ingest(rows, "daily.csv", "owner@example.com")

    assert result["unchanged"] == 1
    assert len(service._read_history()) == 1


def _mixed_csv() -> bytes:
    """Three rows: one good, one with an out-of-range percentage, one non-numeric."""
    return (
        "date,outlet,dine_in_sales,covers,food_cost_pct,labour_cost_pct,"
        "checklist_total,checklist_signed_off,notes\n"
        "2026-09-16,Astra House,214600,182,33.9,26.4,34,33,Closing check\n"
        "2026-09-16,Astra Terrace,171900,131,180.0,25.8,34,33,Bad percentage\n"
        "2026-09-17,Astra House,not-a-number,120,30.0,25.0,34,34,Bad sales\n"
    ).encode()


def test_a_bad_row_is_rejected_without_losing_the_good_rows():
    parsed = service.parse_upload("mixed.csv", _mixed_csv())

    assert len(parsed.records) == 1
    assert parsed.has_rejects
    assert [reject["row"] for reject in parsed.rejects] == [3, 4]
    assert "between 0 and 100" in parsed.rejects[0]["reason"]

    result = service.ingest(parsed.records, "mixed.csv", "owner@example.com")
    assert result["created"] == 1


def test_reject_report_keeps_the_original_values_for_correction():
    parsed = service.parse_upload("mixed.csv", _mixed_csv())
    report = service.reject_report_csv(parsed.rejects)

    lines = report.strip().split("\n")
    assert lines[0].startswith("sheet,row,reason,")
    assert len(lines) == 3
    # the row the reader has to go and fix is carried through verbatim
    assert "Astra Terrace" in report
    assert "not-a-number" in report


def test_a_file_where_every_row_fails_still_reports_rather_than_raises():
    every_row_bad = (
        "date,outlet,dine_in_sales,covers,food_cost_pct,labour_cost_pct,"
        "checklist_total,checklist_signed_off\n"
        "2026-09-16,Astra House,100,10,32.4,25.1,34,99\n"
    ).encode()
    parsed = service.parse_upload("bad.csv", every_row_bad)

    assert parsed.records == []
    assert len(parsed.rejects) == 1


def test_reset_refuses_without_the_confirmation_phrase():
    service.ingest(service.parse_upload("daily.csv", _csv()).records, "daily.csv", "owner@example.com")

    for wrong in ("", "reset", "yes", "RESET please"):
        try:
            service.reset_to_sample(wrong)
        except service.DataImportError:
            pass
        else:
            raise AssertionError(f"reset accepted {wrong!r}")

    # nothing was removed by any of the refused attempts
    assert len(service.current_records()) == 1


def test_reset_discards_uploads_and_returns_to_sample_data():
    parsed = service.parse_upload("mixed.csv", _mixed_csv())
    result = service.ingest(parsed.records, "mixed.csv", "owner@example.com")
    service.store_reject_report(result["batch_id"], parsed.rejects)
    assert service.load_reject_report(result["batch_id"]) is not None

    outcome = service.reset_to_sample("RESET")

    assert outcome["removed_current_records"] == 1
    assert outcome["removed_reject_reports"] == 1
    assert service.current_records() == []
    assert service.current_daily_rows() == []
    # the report went with the batch it described
    assert service.load_reject_report(result["batch_id"]) is None


def test_a_cost_percentage_comes_back_as_the_one_that_was_typed():
    """The figure an operator enters must be the figure the dashboard shows.

    The two cost percentages describe the outlet's whole day. Applying them to
    dine-in sales alone, while reporting them against dine-in plus delivery,
    silently handed back a lower number than the one on the sheet.
    """
    csv_bytes = (
        "date,outlet,dine_in_sales,delivery_sales,covers,food_cost_pct,"
        "labour_cost_pct,checklist_total,checklist_signed_off\n"
        "2026-09-20,Astra House,200000,50000,160,34.0,26.0,34,34\n"
    ).encode()
    service.ingest(service.parse_upload("d.csv", csv_bytes).records, "d.csv", "a@b.c")
    daily = service.current_daily_rows()[0]

    assert daily["total_revenue"] == 250000
    # 34% of the whole 250000 day, not of the 200000 dining-room half
    assert daily["food_cost_amount"] == 85000
    assert daily["food_cost_pct"] == 34.0
    assert daily["labor_cost_pct"] == 26.0
    assert daily["prime_cost_pct"] == 60.0
