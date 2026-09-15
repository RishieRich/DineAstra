"""The document agent.

Retrieves the policy clauses that explain a figure. Retrieval is a scored
keyword match over the numbered sections of data/docs/, which is honest about
what it is: there is no embedding index here, and for four documents there
does not need to be.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ui.backend import analysis
from ui.backend import repository as repo

SECTION_HEADING = re.compile(r"^(#{2,4})\s+(\d+(?:\.\d+)*)\s+(.*)$", re.MULTILINE)
WORD = re.compile(r"[a-z]{4,}")

# Clauses that answer a given intent directly. Checked before the search,
# because for these the right clause is known rather than guessed at.
INTENT_CITATIONS: dict[str, list[tuple[str, str]]] = {
    "food_cost_rise": [("fnb-cost-policy", "3.3"), ("fnb-cost-policy", "2.1")],
    "banquet_margin": [("banquet-policy", "3.4"), ("banquet-policy", "3.1")],
    "requisition_variance": [("expense-policy", "4.1")],
    "checklist": [("brand-standard", "4.2")],
    "segment_comparison": [("banquet-policy", "3.1")],
}


@dataclass
class DocumentPayload:
    citations: list[dict] = field(default_factory=list)
    provenance: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"citations": self.citations, "provenance": self.provenance}


def sections(doc_id: str) -> list[dict]:
    """Every numbered section of one document."""
    text = repo.document_text(doc_id)
    if text is None:
        return []
    numbers = [match.group(2) for match in SECTION_HEADING.finditer(text)]
    found = []
    for number in numbers:
        section = analysis.document_section(doc_id, number)
        if section:
            found.append(section)
    return found


def search(question: str, limit: int = 3) -> list[dict]:
    """Score every section against the question's content words."""
    terms = set(WORD.findall(question.lower()))
    if not terms:
        return []

    scored = []
    for meta in repo.documents_meta():
        for section in sections(meta["id"]):
            body = f"{section['heading']} {section['text']}".lower()
            score = sum(1 for term in terms if term in body)
            if score:
                scored.append((score, {**section, "document_title": meta["title"],
                                       "last_verified": meta.get("last_verified"),
                                       "score": score}))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [section for _, section in scored[:limit]]


def gather(intent: str, question: str) -> DocumentPayload:
    citations = []
    for doc_id, number in INTENT_CITATIONS.get(intent, []):
        citation = analysis._citation(doc_id, number)
        if citation:
            citations.append(citation)

    if not citations:
        citations = search(question)

    return DocumentPayload(
        citations=citations,
        provenance=[
            {
                "source": f"{citation['document_id']}.md",
                "window": f"section {citation['heading_number']}",
                "note": f"last verified {citation.get('last_verified') or 'unknown'}",
            }
            for citation in citations
        ],
    )
