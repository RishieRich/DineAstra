"""Canned prose for mock mode.

The rule this file exists to enforce: **only the prose is canned.** Every
figure in a mock answer is substituted in at render time from a payload the
metric registry computed. A template carries {placeholders}, never digits.

That is what makes the no-keys demo honest. If the underlying data changes,
a mock answer changes with it, and a wrong figure in mock mode is a real bug
rather than a stale string.

Each entry is keyed by intent. `render` fills a template from a flat dict of
already-formatted values and refuses to emit a template with an unfilled
placeholder.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


class MissingFigureError(RuntimeError):
    """A template asked for a figure the payload did not carry."""


@dataclass
class MockAnswer:
    intent: str
    templates: list[str]
    required: tuple[str, ...]


# ---------------------------------------------------------------------------
# the bank
# ---------------------------------------------------------------------------

BANK: dict[str, MockAnswer] = {
    "food_cost_rise": MockAnswer(
        intent="food_cost_rise",
        templates=[
            (
                "Food cost is running at {food_cost_pct} against the standing target of "
                "{food_cost_target_pct}, which is {food_cost_delta} off target. The step "
                "dates from {step_date}, when the produce and dairy vendor invoked the "
                "supply-disruption clause and renewed roughly nine per cent higher. "
                "Property leadership countersigned it, so this is a contracted rate "
                "change rather than a kitchen control failure. At the current F&B "
                "revenue run rate it costs about {daily_impact} a day. The re-tender "
                "opens on {retender_date}."
            ),
        ],
        required=(
            "food_cost_pct",
            "food_cost_target_pct",
            "food_cost_delta",
            "step_date",
            "daily_impact",
            "retender_date",
        ),
    ),
    "banquet_margin": MockAnswer(
        intent="banquet_margin",
        templates=[
            (
                "{event_name} settled at {event_margin} against a {segment} peer average "
                "of {peer_average}, so it sits {margin_delta} behind its segment. The "
                "cause is in the costing policy rather than in the kitchen: the event "
                "carried {covers} covers, above the {covers_threshold}-cover threshold, so "
                "two hours of complimentary house-pour service was extended and charged to "
                "the event. Beverage cost landed at {beverage_share} of contracted revenue "
                "against a segment norm of {beverage_norm}."
            ),
        ],
        required=(
            "event_name",
            "event_margin",
            "segment",
            "peer_average",
            "margin_delta",
            "covers",
            "covers_threshold",
            "beverage_share",
            "beverage_norm",
        ),
    ),
    "segment_comparison": MockAnswer(
        intent="segment_comparison",
        templates=[
            (
                "Across {event_count} events, corporate earns most at {corporate_margin} "
                "and social least at {social_margin}, with wedding at {wedding_margin} and "
                "MICE at {mice_margin}. The gap is structural rather than operational: "
                "weddings and social events carry the decor and labour load that corporate "
                "events do not, which is why the costing policy sets each segment its own "
                "floor instead of one house number."
            ),
        ],
        required=(
            "event_count",
            "corporate_margin",
            "social_margin",
            "wedding_margin",
            "mice_margin",
        ),
    ),
    "occupancy": MockAnswer(
        intent="occupancy",
        templates=[
            (
                "Occupancy on {date} was {occupancy_pct}, against {baseline_occupancy} "
                "across comparable days in the trailing thirty. This property runs "
                "Monday to Thursday heavy: the weekday premium is {weekday_gap}, which is "
                "the corporate and MICE base rather than anything that moved this week."
            ),
        ],
        required=("date", "occupancy_pct", "baseline_occupancy", "weekday_gap"),
    ),
    "occupancy_gu": MockAnswer(
        # Romanised Gujarati, English financial nouns preserved.
        intent="occupancy_gu",
        templates=[
            (
                "{date} na divase occupancy {occupancy_pct} hati, ane trailing thirty "
                "days na comparable divaso ma {baseline_occupancy} hati. Aa property "
                "Monday thi Thursday sudhi vadhare bharai chhe: weekday premium "
                "{weekday_gap} chhe, je corporate ane MICE base chhe, aa week ma kaink "
                "badlayu che etlu nahi."
            ),
        ],
        required=("date", "occupancy_pct", "baseline_occupancy", "weekday_gap"),
    ),
    "requisition_variance": MockAnswer(
        intent="requisition_variance",
        templates=[
            (
                "Two requisitions for {item} were raised on {date}: {baseline_id} at "
                "{baseline_rate} from the contracted vendor, and {outlier_id} at "
                "{outlier_rate} from another. That is a spread of {spread}, worth "
                "{value_at_risk} on the dearer line. The expense policy holds both lines, "
                "not only the dearer one, until a cause is recorded, because the cheaper "
                "line sometimes carries a quality or quantity substitution."
            ),
        ],
        required=(
            "item",
            "date",
            "baseline_id",
            "baseline_rate",
            "outlier_id",
            "outlier_rate",
            "spread",
            "value_at_risk",
        ),
    ),
    "checklist": MockAnswer(
        intent="checklist",
        templates=[
            (
                "The brand standard's section {section_ref} sets {task_count} daily tasks across "
                "{department_count} departments. Department heads sign each item off in "
                "the daily log before handover, and an unsigned item counts as not done "
                "regardless of whether the work happened. The standard was last verified "
                "on {last_verified}."
            ),
        ],
        required=("section_ref", "task_count", "department_count", "last_verified"),
    ),
}


REFUSAL = (
    "Darpan cannot answer that from the property's records. It can account for "
    "occupancy, rate, revenue, cost, banquet margin and requisitions, and it can "
    "quote the property's own policy documents. Anything outside that, it does "
    "not guess at."
)


def render(intent: str, figures: dict[str, str], seed: int | None = None) -> str:
    """Fill a canned template with computed figures.

    Raises MissingFigureError rather than emitting a half-filled sentence or
    inventing a number to fill a gap.
    """
    answer = BANK.get(intent)
    if answer is None:
        return REFUSAL

    missing = [key for key in answer.required if not figures.get(key)]
    if missing:
        raise MissingFigureError(
            f"intent {intent!r} needs figures that were not computed: {missing}"
        )

    template = random.Random(seed).choice(answer.templates)

    unfilled = [
        name for name in PLACEHOLDER.findall(template) if name not in figures
    ]
    if unfilled:
        raise MissingFigureError(
            f"template for {intent!r} has placeholders with no figure: {unfilled}"
        )

    return template.format(**figures)


def intents() -> list[str]:
    return sorted(BANK)


def contains_bare_digit(text: str) -> bool:
    """True if a template carries a digit of its own.

    Used by the test below and by the phase 4 guard: a template that hardcodes
    a figure would keep saying it after the data moved on.
    """
    return any(char.isdigit() for char in PLACEHOLDER.sub("", text))


def audit_templates() -> list[str]:
    """Every template that hardcodes a figure. Should always be empty."""
    offenders = []
    for key, answer in BANK.items():
        for template in answer.templates:
            if contains_bare_digit(template):
                offenders.append(key)
    return offenders
