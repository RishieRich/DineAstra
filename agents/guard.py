"""The number guard.

A model may write the prose. It may not invent the figures.

Every number that appears in a narration is extracted and checked against the
set of numbers the metric agent computed. A narration carrying a figure that
is not in the payload fails, and the caller serves the deterministic template
answer instead of the model's. This is the difference between a demo that is
impressive and one that is safe to put in front of an owner.

The check is deliberately literal: it compares numeric values, not strings, so
"Rs 1,94,000", "194000" and "1,94,000" are the same figure, while "2,00,000"
is not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# A number as it might appear in prose: 55.6, 1,94,000, 4.46, 220.
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")

# Figures the guard does not police: small integers that appear in ordinary
# English ("two hours", "one working day"). Anything above this threshold is a
# claim about the property and is checked.
SMALL_NUMBER_CEILING = 20.0

# "section 3.4", "clause 4.1" -- a pointer to a document, not a claim about a
# figure. Removed before scanning so that 3.4 here is not confused with 3.4
# percentage points somewhere else in the same sentence.
SECTION_REFERENCE = re.compile(
    r"\b(?:section|sections|clause|clauses|rule|paragraph)\s+\d+(?:\.\d+)*",
    re.IGNORECASE,
)


@dataclass
class GuardResult:
    verdict: str  # pass | fail
    unsupported: list[str] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)
    allowed: list[str] = field(default_factory=list)
    reason: str = ""

    @property
    def passed(self) -> bool:
        return self.verdict == "pass"

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "unsupported": self.unsupported,
            "checked": self.checked,
            "reason": self.reason,
        }


def _to_float(raw: str) -> float | None:
    cleaned = raw.replace(",", "").strip().rstrip(".")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_numbers(text: str) -> list[float]:
    """Every number in a piece of text, as floats."""
    values = []
    for match in NUMBER.finditer(text or ""):
        value = _to_float(match.group(0))
        if value is not None:
            values.append(value)
    return values


def allowed_values(payload: dict) -> set[float]:
    """Every number the answer is permitted to contain.

    Drawn from the computed figures, and from the policy clauses the document
    agent retrieved -- a narration may quote a threshold from a clause it was
    given, but may not invent one.
    """
    allowed: set[float] = set()

    for value in (payload.get("figures") or {}).values():
        allowed.update(extract_numbers(str(value)))

    for citation in payload.get("citations") or []:
        allowed.update(extract_numbers(citation.get("text", "")))
        allowed.update(extract_numbers(citation.get("heading", "")))

    for entry in payload.get("provenance") or []:
        for field_name in ("window", "note", "source"):
            allowed.update(extract_numbers(str(entry.get(field_name, ""))))

    return allowed


def check(narration: str, payload: dict, tolerance: float = 0.05) -> GuardResult:
    """Verify a narration against the figures it was given.

    tolerance is absolute and small: it forgives a model writing 55.6 where
    the payload holds 55.60, and forgives nothing else.
    """
    allowed = allowed_values(payload)
    checked: list[str] = []
    unsupported: list[str] = []
    scannable = SECTION_REFERENCE.sub(" ", narration or "")

    for match in NUMBER.finditer(scannable):
        raw = match.group(0)
        value = _to_float(raw)
        if value is None:
            continue
        if value <= SMALL_NUMBER_CEILING and value == int(value):
            continue  # "two hours", "one working day", section 4.2
        checked.append(raw)
        if not any(abs(value - candidate) <= tolerance for candidate in allowed):
            unsupported.append(raw)

    if unsupported:
        return GuardResult(
            verdict="fail",
            unsupported=unsupported,
            checked=checked,
            allowed=sorted(allowed),
            reason=(
                "the narration carried figures that were not in the computed "
                f"payload: {', '.join(unsupported)}"
            ),
        )

    return GuardResult(
        verdict="pass",
        checked=checked,
        allowed=sorted(allowed),
        reason="every figure in the narration is one that was computed",
    )
