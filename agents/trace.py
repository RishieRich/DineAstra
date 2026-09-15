"""Question traces.

One line of JSON per question, in both mock and live mode, appended to
data/runtime/traces.jsonl. The trace records what was asked, how it routed,
which figures were computed, which provider answered, what the guard decided
and whether the model's answer or the template answer was served.

Traces are append-only and never read back by the app. They exist so that
afterwards you can answer "what did it actually say, and was it checked".
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ui.backend import repository as repo

TRACE_PATH = repo.RUNTIME_DIR / "traces.jsonl"
_LOCK = threading.Lock()


def new_trace_id() -> str:
    return uuid.uuid4().hex[:12]


def record(
    *,
    trace_id: str,
    question: str,
    route: dict | None,
    provider: str,
    model: str | None,
    mode: str,
    figures: dict,
    provenance: list,
    citations: list,
    guard_verdict: str | None,
    guard_reason: str,
    served: str,
    answer: str,
    latency_ms: int,
) -> dict:
    """Append one trace line. Never raises into the request path."""
    entry = {
        "trace_id": trace_id,
        "at": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "route": route,
        "provider": provider,
        "model": model,
        "mode": mode,
        "figure_keys": sorted(figures.keys()),
        "figures": figures,
        "provenance": provenance,
        "citations": [
            {
                "document_id": c.get("document_id"),
                "heading": c.get("heading"),
            }
            for c in citations or []
        ],
        "guard": {"verdict": guard_verdict, "reason": guard_reason},
        "served": served,  # model | template | refusal
        "answer": answer,
        "latency_ms": latency_ms,
    }

    try:
        TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, ensure_ascii=False)
        with _LOCK:
            with TRACE_PATH.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line + "\n")
    except OSError:
        # A demo must not fail because a log file could not be written.
        pass

    return entry


def read_recent(limit: int = 20) -> list[dict]:
    """The most recent traces, newest first. Used by the system route."""
    if not TRACE_PATH.exists():
        return []
    lines = TRACE_PATH.read_text(encoding="utf-8").splitlines()
    out = []
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(out) >= limit:
            break
    return out
