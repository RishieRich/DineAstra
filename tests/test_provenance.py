"""Provenance has to name the file a figure actually came from.

The product's whole claim is that any number on the screen can be traced back
to its record. A day an operator uploaded that reports itself as coming from
the seeded dataset breaks that claim quietly, which is the worst way to break
it -- so these tests pin the source line rather than trusting it.
"""

from __future__ import annotations

import pytest

from agents import registry
from ui.backend import data_import_service as service
from ui.backend import repository as repo

SEEDED_DAY = "2026-09-14"
UPLOADED_DAY = "2026-09-19"


@pytest.fixture
def uploaded_day(tmp_path, monkeypatch):
    """One uploaded outlet-day on a date the seeded dataset does not cover."""
    monkeypatch.setattr(service, "HISTORY_PATH", tmp_path / "history.json")
    monkeypatch.setattr(service, "REJECT_DIR", tmp_path / "reject_reports")
    csv_bytes = (
        "date,outlet,dine_in_sales,covers,food_cost_pct,labour_cost_pct,"
        "checklist_total,checklist_signed_off\n"
        f"{UPLOADED_DAY},Astra House,200000,170,30.0,25.0,34,34\n"
    ).encode()
    service.ingest(
        service.parse_upload("daily.csv", csv_bytes).records,
        "daily.csv",
        "owner@example.com",
    )
    return UPLOADED_DAY


def test_a_seeded_day_cites_the_seeded_dataset():
    result = registry.compute("total_revenue", SEEDED_DAY)
    assert result.provenance.source == "daily_property.json"


def test_an_uploaded_day_cites_data_studio(uploaded_day):
    result = registry.compute("total_revenue", uploaded_day)
    assert result.provenance.source == "Data Studio"
    assert result.value == 200000


def test_a_window_spanning_both_cites_both(uploaded_day):
    result = registry.compute("trailing_30_total_revenue", uploaded_day)
    assert result.provenance.source == "daily_property.json + Data Studio"


def test_an_upload_does_not_move_the_demo_today(uploaded_day):
    """A late upload is reachable, but it is not 'today'."""
    assert repo.anchor_date() == repo.ANCHOR_DATE
    assert repo.daily_property_for(uploaded_day) is not None


def test_per_seat_metrics_report_absent_rather_than_zero_on_an_upload(uploaded_day):
    """An outlet sheet says nothing about seat count, and must not imply it did."""
    for key in ("sales_per_seat", "table_turns"):
        result = registry.compute(key, uploaded_day)
        assert result.value is None, key
        assert result.formatted == "--", key


def test_the_load_bearing_figures_survive_an_upload(uploaded_day):
    """The figures the demo script quotes must not drift when data is loaded."""
    assert registry.compute("corporate_avg_margin_pct", SEEDED_DAY).value == 61.2
    assert registry.compute("checklist_signoff_pct", SEEDED_DAY).value == 97.1
    assert registry.compute("food_cost_pct", SEEDED_DAY).value == 34.4
    assert len(registry.METRICS) == 21


def test_event_metrics_cite_data_studio_once_an_event_is_uploaded(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "HISTORY_PATH", tmp_path / "history.json")
    monkeypatch.setattr(service, "REJECT_DIR", tmp_path / "reject_reports")
    events_csv = (
        "event_id,event_name,segment,date,covers,venue,revenue,food_cost,"
        "beverage_cost,labour_cost,other_cost\n"
        "BQ-2026-777,Test Corporate Dinner,corporate,2026-09-10,100,Hall,500000,"
        "120000,30000,60000,20000\n"
    ).encode()
    service.ingest(
        service.parse_upload("events.csv", events_csv).tables,
        "events.csv",
        "owner@example.com",
    )

    result = registry.compute("corporate_avg_margin_pct", SEEDED_DAY)
    assert result.provenance.source == "banquets.json + Data Studio"
    # and the uploaded event is genuinely in the average, not just named
    assert result.context["event_count"] == 7


def test_seeded_event_metrics_cite_only_the_seeded_file():
    result = registry.compute("banquet_avg_margin_pct", SEEDED_DAY)
    assert result.provenance.source == "banquets.json"
