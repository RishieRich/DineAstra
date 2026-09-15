"""Question routing.

Routing is rule-based on purpose. Two reasons: an unsupported question must
refuse without spending a model call, and the same question must route the
same way every time it is asked in a demo.

A route names the intent, the agent that gathers the figures, and whatever
entity the question pinned down (a date, an event, an item).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ui.backend import repository as repo


@dataclass
class Route:
    intent: str
    agent: str  # metric | document | hybrid
    params: dict = field(default_factory=dict)
    matched_on: str = ""

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "agent": self.agent,
            "params": self.params,
            "matched_on": self.matched_on,
        }


# Each rule: intent, agent, and the terms that have to appear. Order matters --
# the first rule whose terms all appear wins.
RULES: list[tuple[str, str, tuple[tuple[str, ...], ...]]] = [
    (
        "food_cost_rise",
        "hybrid",
        (("food cost", "food-cost", "khana cost", "kitchen cost"),),
    ),
    (
        "banquet_margin",
        "hybrid",
        (("margin", "profit", "settled"), ("event", "banquet", "bq-", "kickoff")),
    ),
    (
        "segment_comparison",
        "metric",
        (
            ("segment", "corporate", "wedding", "social", "mice"),
            ("least", "most", "compare", "worst", "best", "earns", "lowest", "highest"),
        ),
    ),
    (
        "requisition_variance",
        "hybrid",
        (("requisition", "rate", "vendor", "purchase", "paid"),
         ("two", "different", "variance", "spread", "twice")),
    ),
    (
        "checklist",
        "document",
        (("checklist", "daily task", "brand standard", "every department", "departments do"),),
    ),
    (
        "occupancy",
        "metric",
        (("occupancy", "rooms sold", "how full"),),
    ),
]

# Romanised Gujarati and Hindi markers. A question in either gets answered in
# the same register it was asked in.
GUJARATI_MARKERS = ("kem", "chhe", "che", "ketlu", "ketla", "aa mahine", "vadhyu", "shu")
HINDI_MARKERS = ("kyun", "kyu", "kitna", "kitni", "hua", "badha", "kaise")

EVENT_ID = re.compile(r"\bBQ-\d{4}-\d{3}\b", re.IGNORECASE)
ISO_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def detect_language(question: str) -> str:
    lowered = f" {question.lower()} "
    if any(f" {marker} " in lowered or marker in lowered for marker in GUJARATI_MARKERS):
        return "gu-latn"
    if any(f" {marker} " in lowered for marker in HINDI_MARKERS):
        return "hi-latn"
    return "en"


def route(question: str) -> Route | None:
    """Return a Route, or None when Darpan should refuse."""
    lowered = question.lower()
    params: dict = {}

    event_match = EVENT_ID.search(question)
    if event_match:
        params["event_id"] = event_match.group(0).upper()

    date_match = ISO_DATE.search(question)
    params["date"] = (
        date_match.group(1) if date_match else repo.anchor_date().isoformat()
    )

    language = detect_language(question)
    params["language"] = language

    # A named event asked about in margin terms routes to that event directly.
    if "event_id" in params and any(
        term in lowered for term in ("margin", "why", "kem", "kyun", "settled")
    ):
        return Route("banquet_margin", "hybrid", params, matched_on="event id")

    for intent, agent, term_groups in RULES:
        if all(any(term in lowered for term in group) for group in term_groups):
            if intent == "occupancy" and language == "gu-latn":
                intent = "occupancy_gu"
            if intent == "banquet_margin" and "event_id" not in params:
                params["event_id"] = _worst_event_id(params["date"])
            return Route(intent, agent, params, matched_on=", ".join(term_groups[0][:2]))

    return None


def _worst_event_id(day: str) -> str:
    """The event a bare 'why is banquet margin down' is really about: the one
    furthest below its segment floor."""
    from agents import registry

    events = [e for e in repo.banquets_all() if e["date"] <= day]
    if not events:
        return ""
    worst = min(
        events,
        key=lambda e: e["margin_pct"] - registry.segment_margin_floor(e["segment"]),
    )
    return worst["id"]
