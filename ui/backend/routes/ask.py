"""The Ask route.

Server-sent events, three event types, always in this order:

    meta   -- intent, provider, figures, provenance, citations. Sent before
              the first token so the screen can show where the answer comes
              from while it is still arriving.
    token  -- one chunk of prose, word by word.
    done   -- guard verdict, what was served, the full text, the trace id.
"""

from __future__ import annotations

import json
from typing import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents import narrator
from ui.backend import auth

router = APIRouter(prefix="/api", tags=["ask"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


def _event(name: str, payload: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stream(question: str) -> Iterator[str]:
    answer = narrator.prepare(question)
    yield _event("meta", answer.meta())
    for chunk in narrator.stream(answer):
        yield _event("token", {"text": chunk})
    yield _event(
        "done",
        {
            "trace_id": answer.trace_id,
            "served": answer.served,
            "guard": {
                "verdict": answer.guard_verdict,
                "reason": answer.guard_reason,
            },
            "text": answer.text,
        },
    )


@router.post("/ask")
def ask(payload: AskRequest, user: dict = Depends(auth.current_user)):
    return StreamingResponse(
        _stream(payload.question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
