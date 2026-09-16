"""Property Brain service layer.

Document listing, document-scoped answers, checklist generation and upload
handling. The Brain's answers are hybrid by default: a clause from the
property's documents, paired with the live figure that clause governs, each
carrying its own provenance.
"""

from __future__ import annotations

import re
import time
import uuid

from agents import checklist_agent, document_agent, mock_bank, narrator
from agents import formatting as fmt
from agents import registry
from ui.backend import repository as repo

DOCUMENT_NOT_FOUND = "No document with that reference."
NO_CHECKLIST_IN_DOCUMENT = (
    "This document has no daily task list to build a checklist from. "
    "The brand standard is the one that does."
)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
ACCEPTED_SUFFIXES = (".md", ".markdown", ".txt")

# Mock mode answers instantly, which reads as fake. A short, honest pause
# makes the generated checklist feel like work rather than a lookup, and it
# matches the pace of the live path.
MOCK_LATENCY_SECONDS = 0.9

# Clauses whose meaning is carried by a live figure. Pairing them is what
# makes a Brain answer hybrid rather than a document search.
CLAUSE_METRICS = {
    ("brand-standard", "4.2"): "checklist_signoff_pct",
    ("brand-standard", "5"): "checklist_signoff_pct",
    ("fnb-cost-policy", "2.1"): "trailing_7_food_cost_pct",
    ("fnb-cost-policy", "2.2"): "trailing_7_food_cost_pct",
    ("fnb-cost-policy", "3.3"): "trailing_7_food_cost_pct",
    ("banquet-policy", "3.1"): "corporate_avg_margin_pct",
    ("banquet-policy", "3.4"): "corporate_avg_margin_pct",
    ("expense-policy", "4.1"): "requisition_variance_count",
}


# ---------------------------------------------------------------------------
# documents
# ---------------------------------------------------------------------------


def documents() -> dict:
    cards = []
    for meta in repo.documents_meta():
        text = repo.document_text(meta["id"]) or ""
        sections = document_agent.sections(meta["id"])
        cards.append(
            {
                **meta,
                "word_count": len(text.split()),
                "section_count": len(sections),
                "has_checklist": _has_checklist(meta["id"]),
                "summary": _summary(text),
            }
        )
    return {"documents": cards, "count": len(cards)}


def document(doc_id: str) -> dict | None:
    meta = repo.document_meta(doc_id)
    text = repo.document_text(doc_id)
    if meta is None or text is None:
        return None
    return {
        **meta,
        "text": text,
        "lines": text.splitlines(),
        "sections": [
            {
                "heading": s["heading"],
                "heading_number": s["heading_number"],
                "line_start": s["line_start"],
                "line_end": s["line_end"],
            }
            for s in document_agent.sections(doc_id)
        ],
    }


def _summary(text: str) -> str:
    for block in text.split("\n\n"):
        cleaned = " ".join(block.split())
        if cleaned and not cleaned.startswith("#") and ":" not in cleaned[:20]:
            return cleaned[:200]
    return ""


def _has_checklist(doc_id: str) -> bool:
    try:
        checklist_agent.generate(doc_id)
        return True
    except (checklist_agent.SectionNotFound, LookupError):
        return False


# ---------------------------------------------------------------------------
# checklist
# ---------------------------------------------------------------------------


def checklist(doc_id: str, section: str | None = None) -> dict | None:
    if repo.document_meta(doc_id) is None:
        return None
    try:
        built = checklist_agent.generate(doc_id, section)
    except (checklist_agent.SectionNotFound, LookupError):
        return None

    if narrator.status().name == "mock":
        time.sleep(MOCK_LATENCY_SECONDS)

    signoff = registry.compute("checklist_signoff_pct", repo.anchor_date())
    payload = built.to_dict()
    payload["provenance"] = [
        {
            "source": f"{doc_id}.md",
            "window": f"section {built.section}",
            "note": f"last verified {built.last_verified}",
        },
        signoff.provenance.to_dict(),
    ]
    payload["today"] = {
        "signoff_formatted": signoff.formatted,
        "tasks_signed_off": signoff.context.get("tasks_signed_off"),
        "tasks_total": signoff.context.get("tasks_total"),
    }
    return payload


# ---------------------------------------------------------------------------
# document-scoped questions
# ---------------------------------------------------------------------------


def answer(question: str, doc_id: str | None = None) -> dict:
    """A hybrid answer: the clause, the live figure it governs, and both
    provenances. Scoped to one document when the screen asks for that."""
    sections = _search(question, doc_id)

    if not sections:
        return {
            "answer": mock_bank.REFUSAL,
            "citations": [],
            "metric": None,
            "provenance": [],
            "scoped_to": doc_id,
        }

    best = sections[0]
    metric = _metric_for(best)
    prose = _compose(question, best, metric)

    provenance = [
        {
            "source": f"{best['document_id']}.md",
            "window": f"section {best['heading_number']}",
            "note": f"last verified {best.get('last_verified') or 'unknown'}",
        }
    ]
    if metric is not None:
        provenance.append(metric.provenance.to_dict())

    return {
        "answer": prose,
        "citations": [
            {
                "document_id": s["document_id"],
                "document_title": s.get("document_title"),
                "heading": s["heading"],
                "heading_number": s["heading_number"],
                "quote": _first_paragraph(s["text"]),
                "last_verified": s.get("last_verified"),
                "line_start": s["line_start"],
                "line_end": s["line_end"],
            }
            for s in sections[:2]
        ],
        "metric": metric.to_dict() if metric else None,
        "provenance": provenance,
        "scoped_to": doc_id,
    }


def _search(question: str, doc_id: str | None) -> list[dict]:
    found = document_agent.search(question, limit=6)
    if doc_id:
        found = [s for s in found if s["document_id"] == doc_id]
    return found


def _metric_for(section: dict):
    key = CLAUSE_METRICS.get((section["document_id"], section["heading_number"]))
    if key is None:
        return None
    return registry.compute(key, repo.anchor_date())


def _compose(question: str, section: dict, metric) -> str:
    """Prose assembled from the clause and the figure. No model call: the
    Brain answers from the document, and the document is already words."""
    clause = _first_paragraph(section["text"])
    verified = section.get("last_verified")

    lines = [
        f"{section.get('document_title', section['document_id'])} section "
        f"{section['heading_number']} covers this."
    ]

    checklist_note = _checklist_note(section)
    if checklist_note:
        lines.append(checklist_note)

    lines.append(f"The clause reads: {clause}")

    if metric is not None and metric.value is not None:
        lines.append(
            f"Against that, {metric.label.lower()} today stands at "
            f"{metric.formatted}"
            + (f", {metric.delta_formatted} {metric.delta_label}." if metric.delta_formatted else ".")
        )

    if verified:
        lines.append(f"That section was last verified on {fmt.format_date_long(verified)}.")

    return " ".join(lines)


def _checklist_note(section: dict) -> str | None:
    if (section["document_id"], section["heading_number"]) != ("brand-standard", "4.2"):
        return None
    try:
        built = checklist_agent.generate("brand-standard", "4.2")
    except LookupError:
        return None
    return (
        f"It sets {built.task_count} daily tasks across "
        f"{built.department_count} departments."
    )


def _first_paragraph(text: str) -> str:
    for block in text.split("\n\n"):
        cleaned = " ".join(block.split())
        if cleaned:
            return cleaned
    return ""


# ---------------------------------------------------------------------------
# upload
# ---------------------------------------------------------------------------


def validate_upload(filename: str | None, content: bytes) -> tuple[bool, str, str]:
    """Returns (accepted, reason_code, detail). The reason code is what the
    route maps to a status; the detail is what the person reads."""
    name = (filename or "").lower()

    if not name.endswith(ACCEPTED_SUFFIXES):
        return False, "unsupported_type", (
            "DineAstra reads markdown and plain text. Convert the file to .md or "
            ".txt and upload it again."
        )

    if len(content) > MAX_UPLOAD_BYTES:
        return False, "too_large", (
            f"That file is {fmt.format_number(len(content) // (1024 * 1024))} MB. "
            f"The limit is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB. Split it or "
            f"upload the section you need."
        )

    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return False, "not_utf8", (
            "That file is not UTF-8 text. Save it as UTF-8 and upload it again."
        )

    return True, "accepted", "accepted"


def store_upload(filename: str, content: bytes) -> dict:
    text = content.decode("utf-8")
    doc_id = _slug(filename)
    meta = repo.add_session_document(
        doc_id=doc_id,
        title=_title_from(text, filename),
        filename=filename,
        text=text,
    )
    return {
        **meta,
        "searchable": True,
        "note": "Uploaded for this session only. It is searchable straight away.",
    }


def _slug(filename: str) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", filename.lower().rsplit(".", 1)[0]).strip("-")
    return f"{stem or 'upload'}-{uuid.uuid4().hex[:6]}"


def _title_from(text: str, filename: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
