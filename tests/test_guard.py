"""Guard tests -- the acceptance criteria from the build plan, phase 4."""

from __future__ import annotations

from agents import guard


PAYLOAD = {
    "figures": {
        "event_margin": "55.6%",
        "peer_average": "61.2%",
        "net": "\u20B91,94,000",
        "covers": "220",
    },
    "citations": [],
    "provenance": [{"source": "banquets.json", "window": "6 corporate events"}],
}


def test_guard_fails_on_an_invented_figure():
    """The criterion: a narration saying Rs 2,00,000 when the payload holds
    Rs 1,94,000 must fail."""
    narration = (
        "The event settled at 55.6% against a peer average of 61.2%, "
        "leaving a net of \u20B92,00,000."
    )
    result = guard.check(narration, PAYLOAD)
    assert result.verdict == "fail", result.to_dict()
    assert "2,00,000" in result.unsupported


def test_guard_passes_a_correct_narration():
    narration = (
        "The event settled at 55.6% against a peer average of 61.2%, "
        "leaving a net of \u20B91,94,000 across 220 covers."
    )
    result = guard.check(narration, PAYLOAD)
    assert result.verdict == "pass", result.to_dict()
    assert result.unsupported == []


def test_guard_ignores_small_ordinary_numbers():
    """"two hours", "one working day" and section numbers are prose, not claims."""
    narration = "Two hours of service were extended, per section 3.4 of the policy."
    assert guard.check(narration, PAYLOAD).verdict == "pass"


def test_guard_allows_a_threshold_quoted_from_a_retrieved_clause():
    payload = {
        "figures": {"food_cost_pct": "34.5%"},
        "citations": [
            {
                "heading": "3.3 Produce and dairy rate revision",
                "text": "renewed at rates approximately nine per cent above the "
                "previous schedule, a step of roughly three and a half points "
                "from the 31.0 per cent standing target.",
            }
        ],
    }
    narration = "Food cost is 34.5% against the 31.0% standing target."
    assert guard.check(narration, payload).verdict == "pass"


def test_guard_catches_a_figure_that_is_close_but_wrong():
    narration = "The event settled at 56.6%."
    result = guard.check(narration, PAYLOAD)
    assert result.verdict == "fail"
    assert "56.6" in result.unsupported


def test_number_formats_are_compared_as_values_not_strings():
    payload = {"figures": {"net": "194000"}}
    assert guard.check("The net was \u20B91,94,000.", payload).verdict == "pass"
