"""Data Studio parsing and slowly-changing-dimension behaviour."""

from __future__ import annotations

from ui.backend import data_import_service as service


def _csv(sales: int = 452800) -> bytes:
    return (
        "date,outlet,net_sales,covers,food_cost_pct,labour_cost_pct,"
        "checklist_total,checklist_signed_off,notes\n"
        f"2026-09-16,Astra House,{sales},571,32.4,25.1,34,33,Closing check\n"
    ).encode()


def test_csv_upload_builds_a_current_daily_record(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "HISTORY_PATH", tmp_path / "history.json")
    rows = service.parse_upload("daily.csv", _csv())
    result = service.ingest(rows, "daily.csv", "owner@example.com")

    assert result["created"] == 1
    assert result["updated"] == 0
    daily = service.current_daily_rows()[0]
    assert daily["date"] == "2026-09-16"
    assert daily["total_revenue"] == 452800
    assert daily["checklist_signoff_pct"] == 97.1


def test_changed_business_key_keeps_type_2_history(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "HISTORY_PATH", tmp_path / "history.json")
    service.ingest(service.parse_upload("first.csv", _csv()), "first.csv", "owner@example.com")
    result = service.ingest(
        service.parse_upload("revision.csv", _csv(sales=470000)),
        "revision.csv",
        "owner@example.com",
    )

    history = service._read_history()
    assert result["updated"] == 1
    assert len(history) == 2
    assert [row["is_current"] for row in history] == [False, True]
    assert history[0]["valid_to"] == history[1]["valid_from"]
    assert history[1]["version"] == 2


def test_unchanged_upload_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "HISTORY_PATH", tmp_path / "history.json")
    rows = service.parse_upload("daily.csv", _csv())
    service.ingest(rows, "daily.csv", "owner@example.com")
    result = service.ingest(rows, "daily.csv", "owner@example.com")

    assert result["unchanged"] == 1
    assert len(service._read_history()) == 1
