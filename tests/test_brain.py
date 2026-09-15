"""Property Brain tests: checklist parsing, hybrid answers, uploads."""

from __future__ import annotations

import pytest

from agents import checklist_agent
from ui.backend import brain_service
from ui.backend import repository as repo


def test_checklist_matches_a_hand_count_of_the_document():
    built = checklist_agent.generate("brand-standard")
    assert built.task_count == 34
    assert built.department_count == 6
    assert [d.name for d in built.departments] == [
        "Housekeeping",
        "Front Office",
        "Food & Beverage Service",
        "Kitchen & Stewarding",
        "Banquets & Events",
        "Engineering & Maintenance",
    ]
    # task numbering is contiguous across departments, as the document writes it
    numbers = [t.number for d in built.departments for t in d.tasks]
    assert numbers == list(range(1, 35))


def test_every_task_points_at_the_line_it_came_from():
    built = checklist_agent.generate("brand-standard")
    lines = (repo.document_text("brand-standard") or "").splitlines()
    for department in built.departments:
        for task in department.tasks:
            assert task.text in lines[task.line - 1]


def test_a_document_without_a_task_list_says_so():
    assert brain_service.checklist("banquet-policy") is None


def test_the_brain_chip_pairs_the_clause_with_the_metric():
    result = brain_service.answer(
        "What does the brand standard require every department to do daily?"
    )
    citation = result["citations"][0]
    assert citation["document_id"] == "brand-standard"
    assert citation["heading_number"] == "4.2"
    assert citation["last_verified"] == "2026-09-11"
    assert "11 September 2026" in result["answer"]
    assert result["metric"]["key"] == "checklist_signoff_pct"

    sources = {p["source"] for p in result["provenance"]}
    assert "brand-standard.md" in sources  # the document
    assert "daily_property.json" in sources  # and the metric


def test_a_citation_carries_the_line_span_that_opens_it():
    result = brain_service.answer("What is the food cost target?")
    citation = result["citations"][0]
    assert citation["line_start"] < citation["line_end"]
    lines = (repo.document_text(citation["document_id"]) or "").splitlines()
    quoted = " ".join(
        " ".join(lines[citation["line_start"] : citation["line_end"]]).split()
    )
    assert citation["quote"][:60] in quoted


def test_a_container_section_is_never_cited():
    """Section 4 holds 4.1 and 4.2 and says nothing itself."""
    result = brain_service.answer(
        "What does the brand standard require every department to do daily?"
    )
    assert all(c["heading_number"] != "4" for c in result["citations"])


@pytest.mark.parametrize(
    "filename,reason",
    [
        ("notes.pdf", "unsupported_type"),
        ("big.md", "too_large"),
        ("bad.md", "not_utf8"),
    ],
)
def test_uploads_are_refused_clearly(filename, reason):
    # built here rather than in the parameter list: a multi-megabyte
    # parameter ends up in the test id, and from there in an environment
    # variable that Windows will not accept.
    if reason == "too_large":
        content = b"x" * (brain_service.MAX_UPLOAD_BYTES + 1)
    elif reason == "not_utf8":
        content = b"\xff\xfe\x00binary"
    else:
        content = b"whatever"

    accepted, code, detail = brain_service.validate_upload(filename, content)
    assert not accepted
    assert code == reason
    # the rejection says what to do next, and does not apologise
    assert detail
    for grovel in ("sorry", "apolog", "unfortunately"):
        assert grovel not in detail.lower()


def test_an_uploaded_document_is_searchable_in_the_same_session():
    text = (
        "# Pool Standard\n\n## 1. Daily checks\n\n"
        "Pool water is tested for chlorine at 07:00 and 16:00 each day.\n"
    )
    accepted, _, _ = brain_service.validate_upload("pool.md", text.encode("utf-8"))
    assert accepted

    stored = brain_service.store_upload("pool.md", text.encode("utf-8"))
    assert stored["searchable"]

    result = brain_service.answer("When is pool water tested for chlorine?")
    assert result["citations"]
    assert result["citations"][0]["document_id"] == stored["id"]
