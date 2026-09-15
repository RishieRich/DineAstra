"""The metric registry.

Twenty-one metrics. Every one has a compute function that returns a fully
populated MetricResult: the raw value, the formatted string the UI shows,
and the provenance that says where the figure came from and over what
window. Nothing downstream of this module formats a figure, and nothing
downstream invents one.

A metric compute function takes a MetricContext and returns a MetricResult.
Compute functions never raise on a missing day; they return a MetricResult
with value None and an honest provenance note instead.
"""

from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Callable

from agents import formatting as fmt
from ui.backend import repository as repo

# Policy constants, each traceable to a clause in data/docs/.
FOOD_COST_TARGET_PCT = 31.0  # fnb-cost-policy.md 2.1
FOOD_COST_ESCALATION_PTS = 2.0  # fnb-cost-policy.md 2.2
REQUISITION_VARIANCE_PCT = 40.0  # expense-policy.md 4.1
# banquet-policy.md 3.1 -- one floor per segment, not one house number.
SEGMENT_MARGIN_FLOORS = {
    "corporate": 60.0,
    "mice": 48.0,
    "wedding": 42.0,
    "social": 40.0,
}
CORPORATE_MARGIN_FLOOR_PCT = SEGMENT_MARGIN_FLOORS["corporate"]


def segment_margin_floor(segment: str) -> float:
    return SEGMENT_MARGIN_FLOORS.get(segment, 50.0)
BANQUET_PEER_REVIEW_PTS = 5.0  # banquet-policy.md 4.2
CHECKLIST_TARGET_PCT = 100.0  # brand-standard.md 5
CHECKLIST_OWNER_THRESHOLD_PCT = 95.0  # brand-standard.md 5

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday")
WEEKEND = ("Friday", "Saturday", "Sunday")


@dataclass
class Provenance:
    source: str
    window: str
    note: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MetricResult:
    key: str
    label: str
    value: float | int | None
    formatted: str
    unit: str  # currency | percent | points | count
    provenance: Provenance
    delta: float | None = None
    delta_formatted: str | None = None
    delta_direction: str | None = None  # up | down | flat
    delta_label: str | None = None
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["provenance"] = self.provenance.to_dict()
        return payload


@dataclass
class MetricContext:
    """Everything a compute function is allowed to depend on."""

    day: date

    @property
    def day_iso(self) -> str:
        return self.day.isoformat()


@dataclass
class Metric:
    key: str
    label: str
    unit: str
    description: str
    compute: Callable[[MetricContext], MetricResult]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _missing(key: str, label: str, unit: str, ctx: MetricContext) -> MetricResult:
    return MetricResult(
        key=key,
        label=label,
        value=None,
        formatted="--",
        unit=unit,
        provenance=Provenance(
            source="daily_property.json",
            window=fmt.format_date_long(ctx.day_iso),
            note="no record for this date in the sample dataset",
        ),
        )


def _direction(delta: float | None, higher_is_better: bool = True) -> str | None:
    if delta is None or abs(delta) < 1e-9:
        return "flat"
    improving = delta > 0 if higher_is_better else delta < 0
    return "up" if improving else "down"


def _daily_metric(
    key: str,
    label: str,
    field_name: str,
    unit: str,
    higher_is_better: bool = True,
    decimals: int = 1,
) -> Callable[[MetricContext], MetricResult]:
    """A metric read straight off one day's row, compared with the trailing
    thirty days ending the day before."""

    def compute(ctx: MetricContext) -> MetricResult:
        row = repo.daily_property_for(ctx.day)
        if row is None:
            return _missing(key, label, unit, ctx)

        value = row[field_name]
        # Like-for-like baseline. This property runs Monday-Thursday heavy, so
        # comparing a Monday against a blended thirty-day mean would report a
        # swing that is really just the shape of the week. Weekdays are
        # compared with weekdays and weekend days with weekend days.
        same_day_type = WEEKDAYS if row["day_of_week"] in WEEKDAYS else WEEKEND
        baseline_rows = [
            r
            for r in repo.daily_property_trailing(ctx.day, days=30)
            if r["day_of_week"] in same_day_type
        ]
        baseline = (
            statistics.mean(r[field_name] for r in baseline_rows)
            if baseline_rows
            else None
        )
        delta = round(value - baseline, decimals) if baseline is not None else None
        baseline_label = (
            "Monday to Thursday" if same_day_type is WEEKDAYS else "Friday to Sunday"
        )

        if unit == "currency":
            formatted = fmt.format_currency(value)
            delta_formatted = (
                fmt.format_signed_currency(delta) if delta is not None else None
            )
        elif unit == "percent":
            formatted = fmt.format_percent(value, decimals)
            delta_formatted = fmt.format_points(delta, decimals) if delta is not None else None
        else:
            formatted = fmt.format_number(value)
            delta_formatted = (
                f"{'+' if delta > 0 else ''}{fmt.format_number(delta)}"
                if delta is not None
                else None
            )

        return MetricResult(
            key=key,
            label=label,
            value=value,
            formatted=formatted,
            unit=unit,
            provenance=Provenance(
                source="daily_property.json",
                window=fmt.format_date_long(ctx.day_iso),
                note=f"compared with {len(baseline_rows)} {baseline_label} days in the trailing 30"
                if baseline_rows
                else None,
            ),
            delta=delta,
            delta_formatted=delta_formatted,
            delta_direction=_direction(delta, higher_is_better),
            delta_label=f"against trailing {baseline_label} days"
            if delta is not None
            else None,
            context={"day_of_week": row["day_of_week"]},
        )

    return compute


# ---------------------------------------------------------------------------
# derived / cross-file metrics
# ---------------------------------------------------------------------------


def _compute_trailing_30_revenue(ctx: MetricContext) -> MetricResult:
    rows = repo.daily_property_range(ctx.day, days=30)
    if not rows:
        return _missing("trailing_30_total_revenue", "Total revenue, trailing 30 days", "currency", ctx)
    total = sum(r["total_revenue"] for r in rows)
    return MetricResult(
        key="trailing_30_total_revenue",
        label="Total revenue, trailing 30 days",
        value=total,
        formatted=fmt.format_compact_currency(total),
        unit="currency",
        provenance=Provenance(
            source="daily_property.json",
            window=f"{fmt.format_date_long(rows[0]['date'])} to {fmt.format_date_long(rows[-1]['date'])}",
            note=f"{len(rows)} days of room, F&B and other revenue",
        ),
        context={"days": len(rows), "exact": fmt.format_currency(total)},
    )


def _compute_trailing_7_food_cost(ctx: MetricContext) -> MetricResult:
    rows = repo.daily_property_range(ctx.day, days=7)
    if not rows:
        return _missing("trailing_7_food_cost_pct", "Food cost, trailing 7 days", "percent", ctx)
    value = round(statistics.mean(r["food_cost_pct"] for r in rows), 1)
    delta = round(value - FOOD_COST_TARGET_PCT, 1)
    return MetricResult(
        key="trailing_7_food_cost_pct",
        label="Food cost, trailing 7 days",
        value=value,
        formatted=fmt.format_percent(value),
        unit="percent",
        provenance=Provenance(
            source="daily_property.json",
            window=f"{fmt.format_date_long(rows[0]['date'])} to {fmt.format_date_long(rows[-1]['date'])}",
            note="compared with the 31.0% standing target in fnb-cost-policy.md 2.1",
        ),
        delta=delta,
        delta_formatted=fmt.format_points(delta),
        delta_direction=_direction(delta, higher_is_better=False),
        delta_label="against standing target",
        context={
            "target_pct": FOOD_COST_TARGET_PCT,
            "escalation_pts": FOOD_COST_ESCALATION_PTS,
            "breaches_escalation": delta > FOOD_COST_ESCALATION_PTS,
        },
    )


def _compute_food_cost_vs_target(ctx: MetricContext) -> MetricResult:
    row = repo.daily_property_for(ctx.day)
    if row is None:
        return _missing("food_cost_vs_target_pts", "Food cost against target", "points", ctx)
    delta = round(row["food_cost_pct"] - FOOD_COST_TARGET_PCT, 1)
    return MetricResult(
        key="food_cost_vs_target_pts",
        label="Food cost against target",
        value=delta,
        formatted=fmt.format_points(delta),
        unit="points",
        provenance=Provenance(
            source="daily_property.json",
            window=fmt.format_date_long(ctx.day_iso),
            note="standing target 31.0% per fnb-cost-policy.md 2.1",
        ),
        delta_direction=_direction(delta, higher_is_better=False),
        context={"target_pct": FOOD_COST_TARGET_PCT, "actual_pct": row["food_cost_pct"]},
    )


def _compute_weekday_occupancy_gap(ctx: MetricContext) -> MetricResult:
    rows = repo.daily_property_range(ctx.day, days=28)
    if not rows:
        return _missing("weekday_occupancy_gap_pts", "Weekday occupancy premium", "points", ctx)
    weekday = [r["occupancy_pct"] for r in rows if r["day_of_week"] in WEEKDAYS]
    weekend = [r["occupancy_pct"] for r in rows if r["day_of_week"] in WEEKEND]
    if not weekday or not weekend:
        return _missing("weekday_occupancy_gap_pts", "Weekday occupancy premium", "points", ctx)
    gap = round(statistics.mean(weekday) - statistics.mean(weekend), 1)
    return MetricResult(
        key="weekday_occupancy_gap_pts",
        label="Weekday occupancy premium",
        value=gap,
        formatted=fmt.format_points(gap),
        unit="points",
        provenance=Provenance(
            source="daily_property.json",
            window=f"{fmt.format_date_long(rows[0]['date'])} to {fmt.format_date_long(rows[-1]['date'])}",
            note=f"Monday-Thursday mean against Friday-Sunday mean, {len(rows)} days",
        ),
        context={
            "weekday_mean": round(statistics.mean(weekday), 1),
            "weekend_mean": round(statistics.mean(weekend), 1),
        },
    )


def _compute_banquet_event_count(ctx: MetricContext) -> MetricResult:
    events = [e for e in repo.banquets_all() if e["date"] <= ctx.day_iso]
    return MetricResult(
        key="banquet_event_count",
        label="Banquet events held",
        value=len(events),
        formatted=fmt.format_count(len(events), "event"),
        unit="count",
        provenance=Provenance(
            source="banquets.json",
            window=f"up to {fmt.format_date_long(ctx.day_iso)}",
        ),
        context={"segments": sorted({e["segment"] for e in events})},
    )


def _compute_banquet_revenue_total(ctx: MetricContext) -> MetricResult:
    events = [e for e in repo.banquets_all() if e["date"] <= ctx.day_iso]
    total = sum(e["revenue"] for e in events)
    return MetricResult(
        key="banquet_revenue_total",
        label="Banquet revenue",
        value=total,
        formatted=fmt.format_compact_currency(total),
        unit="currency",
        provenance=Provenance(
            source="banquets.json",
            window=f"{len(events)} events up to {fmt.format_date_long(ctx.day_iso)}",
        ),
        context={"exact": fmt.format_currency(total)},
    )


def _compute_banquet_avg_margin(ctx: MetricContext) -> MetricResult:
    events = [e for e in repo.banquets_all() if e["date"] <= ctx.day_iso]
    if not events:
        return _missing("banquet_avg_margin_pct", "Banquet margin, all segments", "percent", ctx)
    value = round(statistics.mean(e["margin_pct"] for e in events), 1)
    return MetricResult(
        key="banquet_avg_margin_pct",
        label="Banquet margin, all segments",
        value=value,
        formatted=fmt.format_percent(value),
        unit="percent",
        provenance=Provenance(
            source="banquets.json",
            window=f"{len(events)} events up to {fmt.format_date_long(ctx.day_iso)}",
            note="weighted equally per event per banquet-policy.md 5",
        ),
        context={"event_count": len(events)},
    )


def _segment_margin_metric(segment: str, label: str, key: str):
    def compute(ctx: MetricContext) -> MetricResult:
        events = [
            e
            for e in repo.banquets_by_segment(segment)
            if e["date"] <= ctx.day_iso
        ]
        if not events:
            return _missing(key, label, "percent", ctx)
        value = round(statistics.mean(e["margin_pct"] for e in events), 1)
        floor = segment_margin_floor(segment)
        delta = round(value - floor, 1)
        return MetricResult(
            key=key,
            label=label,
            value=value,
            formatted=fmt.format_percent(value),
            unit="percent",
            provenance=Provenance(
                source="banquets.json",
                window=f"{len(events)} {segment} events up to {fmt.format_date_long(ctx.day_iso)}",
                note="weighted equally per event per banquet-policy.md 5",
            ),
            delta=delta,
            delta_formatted=fmt.format_points(delta),
            delta_direction=_direction(delta, higher_is_better=True),
            delta_label=f"against the {fmt.format_percent(floor)} segment floor",
            context={
                "event_count": len(events),
                "segment": segment,
                "floor_pct": floor,
                "event_ids": [e["id"] for e in events],
            },
        )

    return compute


def _compute_checklist_signoff(ctx: MetricContext) -> MetricResult:
    """Brand-standard compliance: the share of section 4.2's daily tasks
    signed off in the daily log. brand-standard.md 5 sets the 100% target and
    the 95% owner reporting threshold."""
    row = repo.daily_property_for(ctx.day)
    if row is None:
        return _missing("checklist_signoff_pct", "Brand standard sign-off", "percent", ctx)

    value = row["checklist_signoff_pct"]
    delta = round(value - CHECKLIST_TARGET_PCT, 1)
    return MetricResult(
        key="checklist_signoff_pct",
        label="Brand standard sign-off",
        value=value,
        formatted=fmt.format_percent(value),
        unit="percent",
        provenance=Provenance(
            source="daily_property.json",
            window=fmt.format_date_long(ctx.day_iso),
            note=(
                f"{row['checklist_tasks_signed_off']} of "
                f"{row['checklist_tasks_total']} daily tasks in brand-standard.md 4.2"
            ),
        ),
        delta=delta,
        delta_formatted=fmt.format_points(delta),
        delta_direction=_direction(delta, higher_is_better=True),
        delta_label="against the 100% target",
        context={
            "tasks_total": row["checklist_tasks_total"],
            "tasks_signed_off": row["checklist_tasks_signed_off"],
            "tasks_missed": row["checklist_tasks_total"] - row["checklist_tasks_signed_off"],
            "target_pct": CHECKLIST_TARGET_PCT,
            "owner_threshold_pct": CHECKLIST_OWNER_THRESHOLD_PCT,
            "below_owner_threshold": value < CHECKLIST_OWNER_THRESHOLD_PCT,
        },
    )


def _compute_requisition_variance_count(ctx: MetricContext) -> MetricResult:
    from ui.backend import analysis  # local import: analysis imports formatting

    pairs = analysis.variance_pairs_for_date(ctx.day_iso)
    return MetricResult(
        key="requisition_variance_count",
        label="Requisitions held for variance review",
        value=len(pairs),
        formatted=fmt.format_count(len(pairs), "item"),
        unit="count",
        provenance=Provenance(
            source="submissions.json",
            window=fmt.format_date_long(ctx.day_iso),
            note=f"same-item unit-rate variance above {fmt.format_percent(REQUISITION_VARIANCE_PCT, 0)} per expense-policy.md 4.1",
        ),
        context={"items": [p["item"] for p in pairs]},
    )


# ---------------------------------------------------------------------------
# the registry
# ---------------------------------------------------------------------------

METRICS: dict[str, Metric] = {}


def _register(metric: Metric) -> None:
    METRICS[metric.key] = metric


for _spec in (
    ("occupancy_pct", "Occupancy", "occupancy_pct", "percent", True, "Rooms sold against rooms available."),
    ("adr", "ADR", "adr", "currency", True, "Average daily rate across sold rooms."),
    ("revpar", "RevPAR", "revpar", "currency", True, "Revenue per available room."),
    ("rooms_sold", "Rooms sold", "rooms_sold", "count", True, "Rooms sold on the day."),
    ("room_revenue", "Room revenue", "room_revenue", "currency", True, "Rooms revenue on the day."),
    ("fnb_revenue", "F&B revenue", "fnb_revenue", "currency", True, "Food and beverage revenue on the day."),
    ("total_revenue", "Total revenue", "total_revenue", "currency", True, "All revenue lines on the day."),
    ("gop_amount", "Gross operating profit", "gop_amount", "currency", True, "Revenue less direct cost."),
    ("gop_pct", "GOP margin", "gop_pct", "percent", True, "Gross operating profit as a share of revenue."),
    ("food_cost_pct", "Food cost", "food_cost_pct", "percent", False, "Food cost as a share of F&B revenue."),
    ("labor_cost_pct", "Labour cost", "labor_cost_pct", "percent", False, "Labour cost as a share of room and F&B revenue."),
):
    _key, _label, _field, _unit, _higher, _desc = _spec
    _register(
        Metric(
            key=_key,
            label=_label,
            unit=_unit,
            description=_desc,
            compute=_daily_metric(_key, _label, _field, _unit, _higher),
        )
    )

_register(Metric("trailing_30_total_revenue", "Total revenue, trailing 30 days", "currency",
                 "Thirty-day revenue, the Overview headline figure.", _compute_trailing_30_revenue))
_register(Metric("trailing_7_food_cost_pct", "Food cost, trailing 7 days", "percent",
                 "Seven-day food cost average against the standing target.", _compute_trailing_7_food_cost))
_register(Metric("food_cost_vs_target_pts", "Food cost against target", "points",
                 "Percentage points above or below the 31% standing target.", _compute_food_cost_vs_target))
_register(Metric("weekday_occupancy_gap_pts", "Weekday occupancy premium", "points",
                 "Monday-Thursday occupancy against Friday-Sunday.", _compute_weekday_occupancy_gap))
_register(Metric("banquet_event_count", "Banquet events held", "count",
                 "Count of banquet events in the dataset to date.", _compute_banquet_event_count))
_register(Metric("banquet_revenue_total", "Banquet revenue", "currency",
                 "Contracted banquet revenue to date.", _compute_banquet_revenue_total))
_register(Metric("banquet_avg_margin_pct", "Banquet margin, all segments", "percent",
                 "Event margin across every segment.", _compute_banquet_avg_margin))
_register(Metric("corporate_avg_margin_pct", "Corporate banquet margin", "percent",
                 "Peer average margin across corporate events.",
                 _segment_margin_metric("corporate", "Corporate banquet margin", "corporate_avg_margin_pct")))
_register(Metric("checklist_signoff_pct", "Brand standard sign-off", "percent",
                 "Share of the 34 daily tasks signed off in the daily log.",
                 _compute_checklist_signoff))
_register(Metric("requisition_variance_count", "Requisitions held for variance review", "count",
                 "Same-item requisition pairs above the 40% variance rule.", _compute_requisition_variance_count))


def compute(key: str, day: date | str) -> MetricResult:
    """Compute one metric by key."""
    metric = METRICS.get(key)
    if metric is None:
        raise KeyError(f"unknown metric: {key}")
    return metric.compute(MetricContext(day=repo.parse_date(day)))


def compute_many(keys: list[str], day: date | str) -> list[MetricResult]:
    return [compute(key, day) for key in keys]


def catalogue() -> list[dict]:
    """The registry as a serialisable list, for the system route."""
    return [
        {
            "key": m.key,
            "label": m.label,
            "unit": m.unit,
            "description": m.description,
        }
        for m in METRICS.values()
    ]
