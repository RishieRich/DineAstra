"""The metric agent.

It gathers the figures an answer is allowed to contain. Every value it
returns is already formatted by the registry, and every one carries
provenance. The narrator may only say numbers that appear in this payload,
and guard.py enforces that.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agents import formatting as fmt
from agents import registry
from ui.backend import analysis
from ui.backend import repository as repo


@dataclass
class FigurePayload:
    intent: str
    figures: dict[str, str] = field(default_factory=dict)
    provenance: list[dict] = field(default_factory=list)
    facts: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "figures": self.figures,
            "provenance": self.provenance,
            "facts": self.facts,
        }


def gather(intent: str, params: dict) -> FigurePayload:
    day = params.get("date") or repo.anchor_date().isoformat()
    builder = _BUILDERS.get(intent)
    if builder is None:
        return FigurePayload(intent=intent)
    return builder(day, params)


# ---------------------------------------------------------------------------
# per-intent gatherers
# ---------------------------------------------------------------------------


def _food_cost(day: str, params: dict) -> FigurePayload:
    trailing = registry.compute("trailing_7_food_cost_pct", day)
    row = repo.daily_property_for(day)
    daily_impact = (
        round(row["total_revenue"] * trailing.delta / 100) if row and trailing.delta else 0
    )
    return FigurePayload(
        intent="food_cost_rise",
        figures={
            "food_cost_pct": trailing.formatted,
            "food_cost_target_pct": fmt.format_percent(registry.FOOD_COST_TARGET_PCT),
            "food_cost_delta": trailing.delta_formatted,
            "step_date": fmt.format_date_long("2026-08-16"),
            "daily_impact": fmt.format_currency(daily_impact),
            "retender_date": fmt.format_date_long("2026-10-01"),
        },
        provenance=[trailing.provenance.to_dict()],
        facts={
            "cause": "contracted vendor rate revision, countersigned 15 August 2026",
            "citation": analysis._citation("fnb-cost-policy", "3.3"),
        },
    )


def _banquet_margin(day: str, params: dict) -> FigurePayload:
    event = repo.banquet_by_id(params.get("event_id", ""))
    if event is None:
        return FigurePayload(intent="banquet_margin")

    detail = analysis.banquet_detail(event)
    peer = detail["peer"]
    cause = detail["cause"]
    beverage_share = round(event["beverage_cost"] / event["revenue"] * 100, 1)

    return FigurePayload(
        intent="banquet_margin",
        figures={
            "event_name": event["name"],
            "event_margin": fmt.format_percent(event["margin_pct"]),
            "segment": event["segment"],
            "peer_average": peer["average_margin_formatted"],
            "margin_delta": peer["delta_formatted"],
            "covers": str(event["covers"]),
            "covers_threshold": "150",
            "beverage_share": fmt.format_percent(beverage_share),
            "beverage_norm": "four to five per cent",
        },
        provenance=[peer["provenance"], detail["provenance"]],
        facts={"event_id": event["id"], "cause": cause},
    )


def _segment_comparison(day: str, params: dict) -> FigurePayload:
    segments = {}
    for segment in ("corporate", "wedding", "celebration", "group"):
        events = [e for e in repo.banquets_by_segment(segment) if e["date"] <= day]
        if not events:
            continue
        average = round(sum(e["margin_pct"] for e in events) / len(events), 1)
        segments[segment] = average

    count = registry.compute("banquet_event_count", day)
    return FigurePayload(
        intent="segment_comparison",
        figures={
            # the bare count: the template supplies the noun
            "event_count": fmt.format_number(count.value),
            **{
                f"{segment}_margin": fmt.format_percent(value)
                for segment, value in segments.items()
            },
        },
        provenance=[count.provenance.to_dict()],
        facts={"segment_margins": segments},
    )


def _covers(day: str, params: dict) -> FigurePayload:
    """How busy the estate was, and against what.

    A restaurant's baseline is the same day of the week, not the trailing
    mean -- a Tuesday is not a slow Saturday, it is a normal Tuesday.
    """
    covers = registry.compute("covers", day)
    premium = registry.compute("weekend_sales_premium_pts", day)
    average_spend = registry.compute("average_order_value", day)
    baseline = (
        round(covers.value - covers.delta)
        if covers.value is not None and covers.delta is not None
        else None
    )
    intent = "covers_gu" if params.get("language") == "gu-latn" else "covers"
    return FigurePayload(
        intent=intent,
        figures={
            "date": fmt.format_date_long(day),
            "covers": covers.formatted,
            "baseline_covers": fmt.format_number(baseline),
            "average_spend": average_spend.formatted,
            "weekend_premium": premium.formatted,
        },
        provenance=[covers.provenance.to_dict(), premium.provenance.to_dict()],
        facts={"day_of_week": covers.context.get("day_of_week")},
    )


def _requisition_variance(day: str, params: dict) -> FigurePayload:
    pair = analysis.contrast_pair_for_date(day)
    if pair is None:
        return FigurePayload(intent="requisition_variance")
    return FigurePayload(
        intent="requisition_variance",
        figures={
            "item": pair["item"],
            "date": fmt.format_date_long(day),
            "baseline_id": pair["baseline"]["id"],
            "baseline_rate": pair["baseline"]["unit_cost_formatted"],
            "outlier_id": pair["outlier"]["id"],
            "outlier_rate": pair["outlier"]["unit_cost_formatted"],
            "spread": pair["spread_formatted"],
            "value_at_risk": pair["value_at_risk_formatted"],
        },
        provenance=[
            {
                "source": "submissions.json",
                "window": fmt.format_date_long(day),
                "note": "expense-policy.md 4.1",
            }
        ],
        facts={"citation": pair["citation"]},
    )


_BUILDERS = {
    "food_cost_rise": _food_cost,
    "banquet_margin": _banquet_margin,
    "segment_comparison": _segment_comparison,
    "covers": _covers,
    "covers_gu": _covers,
    "requisition_variance": _requisition_variance,
}
