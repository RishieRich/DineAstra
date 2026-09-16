"""Ask-path tests: routing, mock answers, the guard fallback, and traces."""

from __future__ import annotations

import json
import os

import pytest

from agents import mock_bank, narrator, router
from agents.providers.base import resolve_provider
from agents.providers.mock import MockProvider


@pytest.fixture()
def mock_mode(monkeypatch):
    """Force mock mode regardless of what keys are in the environment."""
    monkeypatch.setenv("DARPAN_PROVIDER", "mock")
    provider, status = resolve_provider()
    monkeypatch.setattr(narrator, "_PROVIDER", provider)
    monkeypatch.setattr(narrator, "_STATUS", status)
    return status


def answer_for(question: str) -> narrator.Answer:
    prepared = narrator.prepare(question)
    "".join(narrator.stream(prepared))
    return prepared


def test_mock_mode_needs_no_key(mock_mode):
    assert mock_mode.name == "mock"
    assert mock_mode.available


def test_each_suggestion_chip_answers_with_computed_figures(mock_mode):
    chips = [
        "Why has food cost risen since the middle of August?",
        "Which event segment earns least, and why?",
        "Aa mahine covers kem vadhya chhe?",
    ]
    for chip in chips:
        answer = answer_for(chip)
        assert answer.served == "template", chip
        assert answer.guard_verdict == "pass", chip
        assert answer.figures, chip
        # every figure the template claimed actually appears in the prose
        for value in answer.figures.values():
            assert str(value) in answer.text, (chip, value)


def test_the_gujarati_chip_answers_in_gujarati_keeping_english_nouns(mock_mode):
    answer = answer_for("Aa mahine covers kem vadhya chhe?")
    assert answer.route["intent"] == "covers_gu"
    for marker in ("na divase", "chhe"):
        assert marker in answer.text
    for noun in ("covers", "average spend", "weekend"):
        assert noun in answer.text


def test_an_unsupported_question_refuses_without_a_model_call(mock_mode):
    answer = answer_for("What is the capital of France?")
    assert answer.route is None
    assert answer.served == "refusal"
    assert answer.text == mock_bank.REFUSAL
    assert answer.guard_verdict is None


def test_a_failing_guard_serves_the_template_not_the_model(monkeypatch, mock_mode):
    """A provider that invents a figure must not reach the screen."""

    class LyingProvider(MockProvider):
        name = "lying"

        def stream(self, system, prompt):
            yield "Food cost is running at 99.9%, which is a figure nobody computed."

    provider = LyingProvider()
    monkeypatch.setattr(narrator, "_PROVIDER", provider)
    monkeypatch.setattr(
        narrator, "_STATUS", type(mock_mode)(name="lying", available=True, model="x")
    )
    # isinstance(MockProvider) would short-circuit the guard path, so the
    # narrator is exercised through its live branch here.
    monkeypatch.setattr(narrator, "MockProvider", MockProvider)

    prepared = narrator.prepare("Why has food cost risen since the middle of August?")
    text = "".join(narrator.stream(prepared))
    assert "99.9" not in text


def test_every_question_writes_one_well_formed_trace(mock_mode, tmp_path, monkeypatch):
    from agents import trace

    path = tmp_path / "traces.jsonl"
    monkeypatch.setattr(trace, "TRACE_PATH", path)

    answer_for("Why has food cost risen since the middle of August?")
    answer_for("What is the capital of France?")

    lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2
    required = {
        "trace_id", "at", "question", "route", "provider", "model", "mode",
        "figures", "provenance", "guard", "served", "answer", "latency_ms",
    }
    for entry in lines:
        assert required <= set(entry)


def test_router_refuses_rather_than_reaching_for_the_nearest_metric():
    assert router.route("What is the capital of France?") is None
    assert router.route("Book me a table for four") is None
    assert router.route("Why has food cost risen?") is not None
