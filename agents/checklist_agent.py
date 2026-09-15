"""The checklist agent.

Turns a section of a property document into a reviewable draft checklist:
departments, the tasks under each, and the line each task came from so a
department head can check the draft against the source before adopting it.

Parsing is structural, not statistical. A bold line is a department, a
numbered line beneath it is a task. That is how the property writes its
documents, and a parse that matches the document exactly is worth more here
than one that guesses at documents it has never seen.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from ui.backend import analysis
from ui.backend import repository as repo

DEPARTMENT_LINE = re.compile(r"^\*\*(.+?)\*\*\s*$")
TASK_LINE = re.compile(r"^\s*(\d+)\.\s+(.*\S)\s*$")
BULLET_LINE = re.compile(r"^\s*[-*]\s+(.*\S)\s*$")

# Where a document's daily task list lives, when it has one.
DEFAULT_SECTIONS = {
    "brand-standard": "4.2",
}


@dataclass
class Task:
    number: int
    text: str
    department: str
    line: int


@dataclass
class Department:
    name: str
    tasks: list[Task] = field(default_factory=list)


@dataclass
class Checklist:
    document_id: str
    document_title: str
    section: str
    section_heading: str
    last_verified: str | None
    departments: list[Department]
    task_count: int
    department_count: int
    intro: str
    line_start: int
    line_end: int

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "document_title": self.document_title,
            "section": self.section,
            "section_heading": self.section_heading,
            "last_verified": self.last_verified,
            "intro": self.intro,
            "task_count": self.task_count,
            "department_count": self.department_count,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "departments": [
                {"name": d.name, "task_count": len(d.tasks),
                 "tasks": [asdict(t) for t in d.tasks]}
                for d in self.departments
            ],
            "tasks": [
                asdict(task) for d in self.departments for task in d.tasks
            ],
        }


class SectionNotFound(LookupError):
    """The document has no such section to build a checklist from."""


def generate(doc_id: str, section: str | None = None) -> Checklist:
    """Build a draft checklist from one section of one document."""
    section = section or DEFAULT_SECTIONS.get(doc_id) or _first_task_section(doc_id)
    if section is None:
        raise SectionNotFound(
            f"{doc_id} has no numbered section carrying a task list"
        )

    found = analysis.document_section(doc_id, section)
    if found is None:
        raise SectionNotFound(f"{doc_id} has no section {section}")

    meta = repo.document_meta(doc_id) or {}
    departments, intro = _parse(found["text"])
    _resolve_lines(doc_id, departments, found)

    return Checklist(
        document_id=doc_id,
        document_title=meta.get("title", doc_id),
        section=section,
        section_heading=found["heading"],
        last_verified=meta.get("last_verified"),
        departments=departments,
        task_count=sum(len(d.tasks) for d in departments),
        department_count=len(departments),
        intro=intro,
        line_start=found["line_start"],
        line_end=found["line_end"],
    )


def _resolve_lines(doc_id: str, departments: list["Department"], section: dict) -> None:
    """Point each task at the source line it came from.

    Located by scanning the section's own line range rather than by arithmetic
    on the parsed text: the section body is stripped for display, and any
    offset calculation across that drifts. A cursor keeps two identically
    worded tasks pointing at different lines.
    """
    lines = (repo.document_text(doc_id) or "").splitlines()
    cursor = max(section["line_start"] - 1, 0)
    end = min(section["line_end"], len(lines))

    for department in departments:
        for task in department.tasks:
            for index in range(cursor, end):
                if task.text in lines[index]:
                    task.line = index + 1  # 1-based, as an editor counts
                    cursor = index + 1
                    break


def _parse(text: str) -> tuple[list[Department], str]:
    departments: list[Department] = []
    current: Department | None = None
    intro_lines: list[str] = []
    seen_department = False

    for raw in text.splitlines():
        line = raw.rstrip()

        department_match = DEPARTMENT_LINE.match(line)
        if department_match:
            seen_department = True
            current = Department(name=department_match.group(1).strip())
            departments.append(current)
            continue

        task_match = TASK_LINE.match(line) or BULLET_LINE.match(line)
        if task_match and current is not None:
            groups = task_match.groups()
            number = int(groups[0]) if len(groups) > 1 else len(current.tasks) + 1
            body = groups[-1]
            current.tasks.append(
                Task(
                    number=number,
                    text=body.strip(),
                    department=current.name,
                    line=0,  # filled in by _resolve_lines
                )
            )
            continue

        if not seen_department and line.strip():
            intro_lines.append(line.strip())

    intro = " ".join(intro_lines).strip()
    return [d for d in departments if d.tasks], intro


def _first_task_section(doc_id: str) -> str | None:
    """Any numbered section that parses into at least one department."""
    from agents import document_agent

    for section in document_agent.sections(doc_id):
        departments, _ = _parse(section["text"])
        if departments and any(d.tasks for d in departments):
            return section["heading_number"]
    return None
