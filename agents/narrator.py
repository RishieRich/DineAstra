"""The narrator.

Puts the pieces together: route the question, gather the figures, retrieve
the clauses, get prose from whichever provider resolved, check every figure
in that prose against the payload, and stream the result.

The order matters. Figures are computed before any prose exists, so the
answer is built around the numbers rather than the numbers being fitted to
the answer. In live mode the guard sits between the model and the screen: a
narration carrying a figure that was not computed is discarded and the
deterministic template is streamed instead.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from agents import document_agent, guard, metric_agent, mock_bank, router, trace
from agents.providers.base import ProviderStatus, resolve_provider
from agents.providers.mock import MockProvider

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

# Provider error messages quote the request URL, and Gemini passes its key as
# a query parameter. Nothing that has touched a provider error goes into a
# trace, a log line or an API response without passing through this first.
_SECRET_IN_URL = re.compile(r"(key=)[A-Za-z0-9_\-]{10,}")
_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{10,}")
REDACTION = r"\1[redacted]"


def scrub_secrets(text: str) -> str:
    scrubbed = _SECRET_IN_URL.sub(REDACTION, text or "")
    return _BEARER.sub(REDACTION, scrubbed)

_PROVIDER = None
_STATUS: ProviderStatus | None = None


def startup() -> ProviderStatus:
    """Resolve the provider once, at application start."""
    global _PROVIDER, _STATUS
    _PROVIDER, _STATUS = resolve_provider()
    return _STATUS


def status() -> ProviderStatus:
    if _STATUS is None:
        return startup()
    return _STATUS


def provider():
    if _PROVIDER is None:
        startup()
    return _PROVIDER


def _system_prompt() -> str:
    path = PROMPTS_DIR / "narrator.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


@dataclass
class Answer:
    trace_id: str
    question: str
    route: dict | None
    figures: dict = field(default_factory=dict)
    provenance: list = field(default_factory=list)
    citations: list = field(default_factory=list)
    served: str = "pending"  # pending | model | template | refusal
    guard_verdict: str | None = None
    guard_reason: str = ""
    text: str = ""

    def meta(self) -> dict:
        """The meta event: everything except the prose, sent before the first
        token so the screen can show provenance while the answer streams."""
        return {
            "trace_id": self.trace_id,
            "intent": (self.route or {}).get("intent"),
            "agent": (self.route or {}).get("agent"),
            "provider": status().name,
            "model": status().model,
            "mode": "mock" if status().name == "mock" else "live",
            "figures": self.figures,
            "provenance": self.provenance,
            "citations": [
                {
                    "document_id": c.get("document_id"),
                    "document_title": c.get("document_title"),
                    "heading": c.get("heading"),
                    "heading_number": c.get("heading_number"),
                    "quote": c.get("quote"),
                    "last_verified": c.get("last_verified"),
                    "line_start": c.get("line_start"),
                    "line_end": c.get("line_end"),
                }
                for c in self.citations
            ],
        }


def prepare(question: str) -> Answer:
    """Route and gather. No prose yet, and no model call yet."""
    trace_id = trace.new_trace_id()
    matched = router.route(question)

    if matched is None:
        return Answer(
            trace_id=trace_id,
            question=question,
            route=None,
            served="refusal",
            text=mock_bank.REFUSAL,
        )

    payload = metric_agent.gather(matched.intent, matched.params)
    documents = (
        document_agent.gather(matched.intent, question)
        if matched.agent in ("document", "hybrid")
        else document_agent.DocumentPayload()
    )

    if not payload.figures:
        # Routed, but the data has nothing to say for that date or entity.
        return Answer(
            trace_id=trace_id,
            question=question,
            route=matched.to_dict(),
            served="refusal",
            text=mock_bank.REFUSAL,
        )

    return Answer(
        trace_id=trace_id,
        question=question,
        route=matched.to_dict(),
        figures=payload.figures,
        provenance=payload.provenance + documents.provenance,
        citations=documents.citations,
    )


def _template_answer(answer: Answer) -> str:
    intent = (answer.route or {}).get("intent", "")
    try:
        return mock_bank.render(intent, answer.figures)
    except mock_bank.MissingFigureError:
        return mock_bank.REFUSAL


_LABELS = {
    "food_cost_pct": "food cost, trailing seven days",
    "food_cost_target_pct": "standing food cost target",
    "food_cost_delta": "food cost against target",
    "step_date": "date the step began",
    "daily_impact": "cost per day at the current run rate",
    "retender_date": "date the re-tender opens",
    "event_margin": "this event's settled margin",
    "peer_average": "segment peer average margin",
    "margin_delta": "this event against the peer average",
    "beverage_share": "beverage cost as a share of revenue",
    "beverage_norm": "segment norm for beverage cost",
    "covers_threshold": "covers threshold in the policy",
    "event_count": "number of events",
    "baseline_occupancy": "occupancy across comparable days",
    "weekday_gap": "Monday-Thursday premium over Friday-Sunday",
    "value_at_risk": "value at risk on the dearer line",
    "spread": "unit-rate spread between the two lines",
}


def _label(key: str) -> str:
    return _LABELS.get(key, key.replace("_", " "))


def _model_prompt(answer: Answer) -> str:
    lines = [f"Question: {answer.question}", "", "Computed figures:"]
    for key, value in answer.figures.items():
        # Readable labels, not payload keys: given "food_cost_target_pct" a
        # model will happily write it into the prose verbatim.
        lines.append(f"- {_label(key)}: {value}")
    if answer.citations:
        lines += ["", "Policy clauses retrieved:"]
        for citation in answer.citations:
            lines.append(
                f"- {citation.get('document_title')} section "
                f"{citation.get('heading')}: {citation.get('quote')}"
            )
    lines += [
        "",
        "Write the answer using only the figures above.",
    ]
    return "\n".join(lines)


def stream(answer: Answer) -> Iterator[str]:
    """Yield the answer's prose, word by word, and finish the Answer.

    In mock mode the template is streamed directly. In live mode the model's
    text is collected, checked by the guard, and only then streamed -- the
    guard cannot un-say a word that has already reached the screen, so the
    check happens before the first token goes out.
    """
    started = time.perf_counter()
    active = provider()

    if answer.served == "refusal":
        answer.guard_verdict = None
        answer.guard_reason = "no model call was made"
        yield from MockProvider.stream_text(answer.text)
        _finish(answer, started)
        return

    template = _template_answer(answer)

    if isinstance(active, MockProvider):
        answer.text = template
        answer.served = "template"
        result = guard.check(template, _guard_payload(answer))
        answer.guard_verdict = result.verdict
        answer.guard_reason = result.reason
        yield from MockProvider.stream_text(template)
        _finish(answer, started)
        return

    try:
        narration = "".join(active.stream(_system_prompt(), _model_prompt(answer)))
    except Exception as exc:  # provider failed mid-flight
        answer.text = template
        answer.served = "template"
        answer.guard_verdict = None
        # Only the exception type and a scrubbed message: provider errors
        # quote the request URL, and for Gemini that URL carries the API key.
        answer.guard_reason = (
            "provider failed, template served instead: "
            f"{type(exc).__name__}: {scrub_secrets(str(exc))}"
        )
        yield from MockProvider.stream_text(template)
        _finish(answer, started)
        return

    if not narration.strip():
        # Nothing to check and nothing to say. Serve the template rather than
        # reporting a vacuous pass on an empty string.
        answer.text = template
        answer.served = "template"
        answer.guard_verdict = None
        answer.guard_reason = "the model returned no prose; template served instead"
        yield from MockProvider.stream_text(answer.text)
        _finish(answer, started)
        return

    result = guard.check(narration, _guard_payload(answer))
    answer.guard_verdict = result.verdict
    answer.guard_reason = result.reason

    if result.passed:
        answer.text = narration.strip()
        answer.served = "model"
    else:
        answer.text = template
        answer.served = "template"

    yield from MockProvider.stream_text(answer.text)
    _finish(answer, started)


def _guard_payload(answer: Answer) -> dict:
    return {
        "figures": answer.figures,
        "citations": answer.citations,
        "provenance": answer.provenance,
    }


def _finish(answer: Answer, started: float) -> None:
    trace.record(
        trace_id=answer.trace_id,
        question=answer.question,
        route=answer.route,
        provider=status().name,
        model=status().model,
        mode="mock" if status().name == "mock" else "live",
        figures=answer.figures,
        provenance=answer.provenance,
        citations=answer.citations,
        guard_verdict=answer.guard_verdict,
        guard_reason=answer.guard_reason,
        served=answer.served,
        answer=answer.text,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
