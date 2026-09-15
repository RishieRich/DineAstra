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

SECTION_HEADING = re.compile(r"^(#{2,4})\s+(\d+(?:\.\d+)*)\.?\s+(.*)$", re.MULTILINE)
UNNUMBERED_HEADING = re.compile(r"^(#{2,4})\s+(?!\d)(.+)$", re.MULTILINE)
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
    """Every section of one document.

    Numbered sections are preferred, because the property's own documents are
    written that way and a citation to "section 4.2" can be opened exactly.
    An uploaded document may have unnumbered headings or none at all; it is
    still split into something citable rather than being left unsearchable.
    """
    text = repo.document_text(doc_id)
    if text is None:
        return []

    numbers = [match.group(2) for match in SECTION_HEADING.finditer(text)]
    found = []
    for number in numbers:
        section = analysis.document_section(doc_id, number)
        if section:
            found.append(section)
    if found:
        return found

    return _unnumbered_sections(doc_id, text)


def _unnumbered_sections(doc_id: str, text: str) -> list[dict]:
    lines = text.splitlines()
    starts = [
        (index, match.group(2).strip())
        for index, line in enumerate(lines)
        for match in [UNNUMBERED_HEADING.match(line)]
        if match
    ]

    if not starts:
        # No headings at all: the document is one section.
        return [
            {
                "document_id": doc_id,
                "heading": "the document",
                "heading_number": "1",
                "text": text.strip(),
                "line_start": 1,
                "line_end": len(lines),
            }
        ]

    out = []
    for position, (index, title) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        out.append(
            {
                "document_id": doc_id,
                "heading": f"{position + 1} {title}",
                "heading_number": str(position + 1),
                "text": "\n".join(lines[index + 1 : end]).strip(),
                "line_start": index + 1,
                "line_end": end,
            }
        )
    return out


# A word that appears in most of these documents carries little signal about
# which clause is wanted.
STOPWORDS = {
    "does", "this", "that", "with", "from", "have", "what", "when", "which",
    "must", "each", "every", "will", "shall", "they", "them", "than", "then",
    "document", "property", "policy", "section",
}


def own_text(text: str) -> str:
    """A section's own prose: everything before its first sub-heading.

    "## 4 Daily departmental standards" contains 4.1 and 4.2 and says nothing
    itself. Quoting it would quote its children's headings, and scoring it
    would let a container outrank the clause that actually answers the
    question.
    """
    out = []
    for line in (text or "").splitlines():
        if line.lstrip().startswith("#"):
            break
        out.append(line)
    return "\n".join(out).strip()


def search(question: str, limit: int = 3) -> list[dict]:
    """Score every section against the question's content words.

    A term in the heading counts for far more than a term buried in the body:
    a heading is the clause's own description of itself. Body matches are
    normalised by length so a long section cannot win on volume alone.
    """
    terms = {t for t in WORD.findall(question.lower()) if t not in STOPWORDS}
    if not terms:
        return []

    scored = []
    for meta in repo.documents_meta():
        # A question that names the document ("what does the brand standard
        # require") is telling you which document to read. Weight that first.
        title = meta["title"].lower()
        title_hits = sum(1 for term in terms if term in title)

        for section in sections(meta["id"]):
            body_text = own_text(section["text"])
            if not body_text:
                continue  # a container section, not a clause

            heading = section["heading"].lower()
            body = body_text.lower()
            body_words = max(len(body.split()), 1)

            heading_hits = sum(1 for term in terms if term in heading)
            body_hits = sum(1 for term in terms if term in body)
            if not heading_hits and not body_hits:
                continue

            score = (
                title_hits * 5
                + heading_hits * 4
                + body_hits
                + (body_hits / body_words) * 8  # density, not volume
            )
            scored.append(
                (
                    round(score, 3),
                    {
                        **section,
                        "own_text": body_text,
                        "document_title": meta["title"],
                        "last_verified": meta.get("last_verified"),
                        "score": round(score, 3),
                    },
                )
            )

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
