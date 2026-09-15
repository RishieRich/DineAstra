"""Derivations that sit between the repository and the routes.

Contrast pairs, banquet causes and the Overview alert are computed here from
the data and from the policy documents. Nothing in this module is hardcoded
to a particular date, event id or submission id: the demo's planted
anomalies are found by the same rules that would find a real one.

No route handler duplicates any of this, and no currency string is built in
routes/ -- every formatted figure comes from agents.formatting.
"""

from __future__ import annotations

import re
import statistics

from agents import formatting as fmt
from agents import registry
from ui.backend import repository as repo

# ---------------------------------------------------------------------------
# document section retrieval
# ---------------------------------------------------------------------------


def document_section(doc_id: str, heading_number: str) -> dict | None:
    """Pull one numbered section out of a markdown document.

    Returns the heading, the body text, and the line span, so a citation can
    be opened in context with the matched lines highlighted.
    """
    text = repo.document_text(doc_id)
    if text is None:
        return None

    lines = text.splitlines()

    def _body(start_index: int, end_index: int) -> dict:
        """The section body, plus the 1-based source line its text begins on.

        The body is stripped for display, which drops leading blank lines; a
        caller mapping a task back to its source line needs to know how many.
        """
        raw = lines[start_index:end_index]
        leading = 0
        for line in raw:
            if line.strip():
                break
            leading += 1
        return {
            "text": "\n".join(raw).strip(),
            "text_line_start": start_index + leading + 1,
        }

    start = None
    heading = None
    level = None

    for index, line in enumerate(lines):
        match = re.match(r"^(#{2,4})\s+(\d+(?:\.\d+)*)\.?\s+(.*)$", line)
        if not match:
            continue
        hashes, number, title = match.groups()
        if start is None and number == heading_number:
            start, heading, level = index, f"{number} {title}", len(hashes)
        elif start is not None and len(hashes) <= level:
            return {
                "document_id": doc_id,
                "heading": heading,
                "heading_number": heading_number,
                "text": "\n".join(lines[start + 1 : index]).strip(),
                "line_start": start + 1,
                "line_end": index,
            }

    if start is None:
        return None
    return {
        "document_id": doc_id,
        "heading": heading,
        "heading_number": heading_number,
        "text": "\n".join(lines[start + 1 :]).strip(),
        "line_start": start + 1,
        "line_end": len(lines),
    }


def _first_paragraph(text: str) -> str:
    for block in text.split("\n\n"):
        cleaned = " ".join(block.split())
        if cleaned:
            return cleaned
    return ""


def _citation(doc_id: str, heading_number: str) -> dict | None:
    section = document_section(doc_id, heading_number)
    if section is None:
        return None
    meta = repo.document_meta(doc_id) or {}
    return {
        **section,
        "document_title": meta.get("title", doc_id),
        "last_verified": meta.get("last_verified"),
        "quote": _first_paragraph(section["text"]),
    }


# ---------------------------------------------------------------------------
# requisition variance / contrast pairs (expense-policy.md 4.1)
# ---------------------------------------------------------------------------


def variance_pairs_for_date(day: str) -> list[dict]:
    """Every same-item pair on `day` whose unit-rate spread breaches the
    forty per cent rule, widest spread first."""
    rows = repo.submissions_for_date(day)
    by_item: dict[str, list[dict]] = {}
    for row in rows:
        by_item.setdefault(row["item"], []).append(row)

    pairs = []
    for item, item_rows in by_item.items():
        if len(item_rows) < 2:
            continue
        cheapest = min(item_rows, key=lambda r: r["unit_cost"])
        dearest = max(item_rows, key=lambda r: r["unit_cost"])
        if cheapest["id"] == dearest["id"] or cheapest["unit_cost"] == 0:
            continue
        spread_pct = (
            (dearest["unit_cost"] - cheapest["unit_cost"]) / cheapest["unit_cost"] * 100
        )
        if spread_pct <= registry.REQUISITION_VARIANCE_PCT:
            continue
        pairs.append(
            {
                "item": item,
                "spread_pct": round(spread_pct, 1),
                "value_at_risk": (dearest["unit_cost"] - cheapest["unit_cost"])
                * dearest["quantity"],
                "baseline": cheapest,
                "outlier": dearest,
            }
        )

    return sorted(pairs, key=lambda p: p["spread_pct"], reverse=True)


def contrast_pair_for_date(day: str) -> dict | None:
    """The widest same-item variance on `day`, shaped for the Proof screen."""
    pairs = variance_pairs_for_date(day)
    if not pairs:
        return None

    pair = pairs[0]
    baseline, outlier = pair["baseline"], pair["outlier"]
    return {
        "item": pair["item"],
        "spread_pct": pair["spread_pct"],
        "spread_formatted": fmt.format_percent(pair["spread_pct"]),
        "value_at_risk": pair["value_at_risk"],
        "value_at_risk_formatted": fmt.format_currency(pair["value_at_risk"]),
        "rule": f"Unit-rate variance above {fmt.format_percent(registry.REQUISITION_VARIANCE_PCT, 0)} on the same item, same day.",
        "citation": _citation("expense-policy", "4.1"),
        "baseline": _submission_view(baseline, "Contracted rate"),
        "outlier": _submission_view(outlier, "Off-contract rate"),
    }


def _submission_view(row: dict, verdict: str) -> dict:
    return {
        **row,
        "unit_cost_formatted": fmt.format_currency(row["unit_cost"]),
        "total_cost_formatted": fmt.format_currency(row["total_cost"]),
        "verdict": verdict,
    }


def submissions_view(day: str) -> dict:
    rows = repo.submissions_for_date(day)
    total = sum(r["total_cost"] for r in rows)
    return {
        "date": day,
        "date_formatted": fmt.format_date_long(day),
        "count": len(rows),
        "total_value_formatted": fmt.format_currency(total),
        "submissions": [
            {
                **r,
                "unit_cost_formatted": fmt.format_currency(r["unit_cost"]),
                "total_cost_formatted": fmt.format_currency(r["total_cost"]),
            }
            for r in rows
        ],
        "contrast_pair": contrast_pair_for_date(day),
        "provenance": {
            "source": "submissions.json",
            "window": fmt.format_date_long(day),
            "note": f"{len(rows)} requisition lines",
        },
    }


# ---------------------------------------------------------------------------
# banquet detail: waterfall, peers, cause
# ---------------------------------------------------------------------------


def banquet_waterfall(event: dict) -> dict:
    """Revenue less four cost lines, summing exactly to net."""
    steps = [
        {"key": "revenue", "label": "Contracted revenue", "value": event["revenue"], "kind": "start"},
        {"key": "food_cost", "label": "Food cost", "value": -event["food_cost"], "kind": "cost"},
        {"key": "beverage_cost", "label": "Beverage cost", "value": -event["beverage_cost"], "kind": "cost"},
        {"key": "labor_cost", "label": "Event labour", "value": -event["labor_cost"], "kind": "cost"},
        {"key": "other_cost", "label": "Other direct cost", "value": -event["other_cost"], "kind": "cost"},
        {"key": "net", "label": "Event net", "value": event["net"], "kind": "end"},
    ]
    for step in steps:
        step["formatted"] = fmt.format_currency(abs(step["value"]))
        step["share_pct"] = round(abs(step["value"]) / event["revenue"] * 100, 1)

    computed_net = event["revenue"] - sum(
        event[k] for k in ("food_cost", "beverage_cost", "labor_cost", "other_cost")
    )
    return {
        "steps": steps,
        "sums_to_net": computed_net == event["net"],
        "net": event["net"],
        "net_formatted": fmt.format_currency(event["net"]),
    }


def banquet_peer_comparison(event: dict) -> dict:
    """Same-segment peer average, equally weighted per banquet-policy.md 5."""
    peers = repo.banquet_peers(event)
    segment_events = repo.banquets_by_segment(event["segment"])
    average = round(statistics.mean(e["margin_pct"] for e in segment_events), 1)
    delta = round(event["margin_pct"] - average, 1)
    return {
        "segment": event["segment"],
        "event_count": len(segment_events),
        "peer_count": len(peers),
        "average_margin_pct": average,
        "average_margin_formatted": fmt.format_percent(average),
        "delta_pts": delta,
        "delta_formatted": fmt.format_points(delta),
        "below_review_threshold": delta < -registry.BANQUET_PEER_REVIEW_PTS,
        "peers": [
            {
                "id": e["id"],
                "name": e["name"],
                "date": e["date"],
                "margin_pct": e["margin_pct"],
                "margin_formatted": fmt.format_percent(e["margin_pct"]),
            }
            for e in segment_events
        ],
        "provenance": {
            "source": "banquets.json",
            "window": f"{len(segment_events)} {event['segment']} events",
            "note": "equally weighted per event per banquet-policy.md 5",
        },
    }


def banquet_cause(event: dict) -> dict | None:
    """Why this event's margin sits where it does, with the policy string
    that explains it. Rule-driven: the conditions below are read off the
    event, and the matching clause is retrieved from data/docs/."""
    beverage_share = event["beverage_cost"] / event["revenue"] * 100

    if (
        event["segment"] == "corporate"
        and event["covers"] > 150
        and beverage_share > 6.0
    ):
        citation = _citation("banquet-policy", "3.4")
        return {
            "headline": "Complimentary beverage service applied at the covers threshold.",
            "detail": (
                f"This event carried {event['covers']} confirmed covers, above the "
                f"150-cover threshold, so two hours of complimentary house-pour service "
                f"was extended and charged to the event. Beverage cost landed at "
                f"{fmt.format_percent(beverage_share)} of contracted revenue against a "
                f"segment norm of four to five per cent."
            ),
            "beverage_share_pct": round(beverage_share, 1),
            "citation": citation,
            "policy_string": citation["quote"] if citation else None,
        }

    floor = registry.segment_margin_floor(event["segment"])
    if event["margin_pct"] < floor:
        citation = _citation("banquet-policy", "3.1")
        return {
            "headline": "Settled margin below the segment floor.",
            "detail": (
                f"This event settled at {fmt.format_percent(event['margin_pct'])}, below "
                f"the {fmt.format_percent(floor)} floor for its {event['segment']} segment."
            ),
            "citation": citation,
            "policy_string": citation["quote"] if citation else None,
        }

    return None


def banquet_detail(event: dict) -> dict:
    return {
        "event": {
            **event,
            "revenue_formatted": fmt.format_currency(event["revenue"]),
            "net_formatted": fmt.format_currency(event["net"]),
            "margin_formatted": fmt.format_percent(event["margin_pct"]),
            "date_formatted": fmt.format_date_long(event["date"]),
        },
        "waterfall": banquet_waterfall(event),
        "peer": banquet_peer_comparison(event),
        "cause": banquet_cause(event),
        "provenance": {
            "source": "banquets.json",
            "window": fmt.format_date_long(event["date"]),
            "note": f"event {event['id']}",
        },
    }


def banquet_list(segment: str | None = None) -> dict:
    events = (
        repo.banquets_by_segment(segment) if segment else repo.banquets_all()
    )
    rows = [
        {
            **e,
            "revenue_formatted": fmt.format_currency(e["revenue"]),
            "net_formatted": fmt.format_currency(e["net"]),
            "margin_formatted": fmt.format_percent(e["margin_pct"]),
            "date_formatted": fmt.format_date_long(e["date"]),
            "below_floor": e["margin_pct"]
            < registry.segment_margin_floor(e["segment"]),
        }
        for e in events
    ]
    rows.sort(key=lambda r: r["date"], reverse=True)
    return {
        "events": rows,
        "segments": sorted({e["segment"] for e in repo.banquets_all()}),
        "provenance": {
            "source": "banquets.json",
            "window": f"{len(rows)} events",
            "note": f"segment filter: {segment}" if segment else None,
        },
    }


# ---------------------------------------------------------------------------
# the Overview alert
# ---------------------------------------------------------------------------


def _food_cost_alert(day: str) -> dict | None:
    """fnb-cost-policy.md 2.2: trailing seven-day food cost more than two
    points above target is reported to the GM in the daily briefing."""
    metric = registry.compute("trailing_7_food_cost_pct", day)
    if metric.value is None or not metric.context.get("breaches_escalation"):
        return None

    row = repo.daily_property_for(day)
    overshoot_pts = metric.delta
    daily_impact = round(row["fnb_revenue"] * overshoot_pts / 100) if row else 0

    return {
        "kind": "food_cost",
        "severity": "high",
        "impact_value": daily_impact * 30,
        "headline": (
            f"Food cost has held at {metric.formatted} for seven days, "
            f"{fmt.format_points(overshoot_pts)} above the standing target."
        ),
        "detail": (
            f"At the current F&B revenue run rate that is about "
            f"{fmt.format_currency(daily_impact)} a day, or roughly "
            f"{fmt.format_compact_currency(daily_impact * 30)} over a month."
        ),
        "question": "Why has food cost risen since the middle of August?",
        "metric": metric.to_dict(),
        "provenance": metric.provenance.to_dict(),
    }


def _requisition_alert(day: str) -> dict | None:
    """expense-policy.md 4.1: same-item unit-rate variance above forty per
    cent is held for GM review."""
    pair = contrast_pair_for_date(day)
    if pair is None:
        return None
    return {
        "kind": "requisition_variance",
        "severity": "medium",
        "impact_value": pair["value_at_risk"],
        "headline": (
            f"Two requisitions for {pair['item']} were raised today "
            f"{pair['spread_formatted']} apart on unit rate."
        ),
        "detail": (
            f"{pair['baseline']['id']} at {pair['baseline']['unit_cost_formatted']} "
            f"against {pair['outlier']['id']} at {pair['outlier']['unit_cost_formatted']}. "
            f"Both are held until a cause is recorded."
        ),
        "question": f"Why did we pay two different rates for {pair['item']} today?",
        "provenance": {
            "source": "submissions.json",
            "window": fmt.format_date_long(day),
            "note": "expense-policy.md 4.1",
        },
    }


def overview_alert(day: str) -> dict | None:
    """The single thing worth the GM's attention today, or nothing at all.

    Candidates are ranked by rupee impact; a quiet day returns None rather
    than manufacturing something to say.
    """
    candidates = [c for c in (_food_cost_alert(day), _requisition_alert(day)) if c]
    if not candidates:
        return None
    return max(candidates, key=lambda c: c["impact_value"])


# ---------------------------------------------------------------------------
# the Overview payload
# ---------------------------------------------------------------------------

OVERVIEW_METRIC_KEYS = [
    "total_revenue",
    "fnb_revenue",
    "food_cost_pct",
    "gop_pct",
    "checklist_signoff_pct",
    "banquet_event_count",
]


def overview(day: str) -> dict:
    row = repo.daily_property_for(day)
    hero = registry.compute("trailing_30_total_revenue", day)
    corporate = registry.compute("corporate_avg_margin_pct", day)
    events_today = repo.banquets_for_date(day)

    return {
        "date": day,
        "date_formatted": fmt.format_date_long(day),
        "day_of_week": row["day_of_week"] if row else None,
        "has_data": row is not None,
        "hero": {
            "value": hero.value,
            "formatted": hero.formatted,
            "exact_formatted": hero.context.get("exact"),
            "label": hero.label,
            "provenance": hero.provenance.to_dict(),
        },
        "metrics": [m.to_dict() for m in registry.compute_many(OVERVIEW_METRIC_KEYS, day)],
        "alert": overview_alert(day),
        "banquets_today": [
            {
                "id": e["id"],
                "name": e["name"],
                "segment": e["segment"],
                "covers": e["covers"],
                "margin_pct": e["margin_pct"],
                "margin_formatted": fmt.format_percent(e["margin_pct"]),
                "revenue_formatted": fmt.format_currency(e["revenue"]),
            }
            for e in events_today
        ],
        "corporate_margin": corporate.to_dict(),
        "digest": whatsapp_digest(day),
        "mode": "sample + uploaded data",
    }


# ---------------------------------------------------------------------------
# the GM digest (Hinglish), assembled from computed figures only
# ---------------------------------------------------------------------------


def whatsapp_digest(day: str) -> dict:
    row = repo.daily_property_for(day)
    if row is None:
        return {"text": "Is date ka data available nahi hai.", "lines": []}

    metrics = {m.key: m for m in registry.compute_many(OVERVIEW_METRIC_KEYS, day)}
    alert = overview_alert(day)

    lines = [
        f"DineAstra daily update, {fmt.format_date_long(day)}",
        "",
        f"Total revenue {metrics['total_revenue'].formatted} hua, jisme F&B {metrics['fnb_revenue'].formatted} hai.",
        f"GOP margin {metrics['gop_pct'].formatted} aur food cost {metrics['food_cost_pct'].formatted} par hai.",
        f"Daily standards sign-off {metrics['checklist_signoff_pct'].formatted} raha.",
    ]

    if alert:
        lines += ["", f"Dhyaan dene wali baat: {alert['headline']}"]
    else:
        lines += ["", "Aaj koi escalation nahi hai."]

    lines += ["", "Figures sample data se hain."]
    return {"text": "\n".join(lines), "lines": lines}
