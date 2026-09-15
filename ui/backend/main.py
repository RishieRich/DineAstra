"""Darpan backend entrypoint.

Run from the repo root:

    uvicorn ui.backend.main:app --port 8000 --reload
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents import narrator
from ui.backend.routes import ask, banquet, operations, overview, system

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

# httpx logs every request line at INFO, and the Gemini endpoint carries the
# API key as a query parameter. Nothing is worth putting a live key in a log
# file, so httpx only speaks up here when something actually goes wrong.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

app = FastAPI(title="Darpan API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(overview.router)
app.include_router(banquet.router)
app.include_router(operations.router)
app.include_router(ask.router)


@app.on_event("startup")
def resolve_provider_at_startup() -> None:
    """Rule VIII: validate the configured model before serving, not during a
    question. A bad model id logs the ids that are available and falls through
    to the next provider; the app serves every screen either way."""
    status = narrator.startup()
    logging.getLogger("darpan").info(
        "Answering through %s (%s): %s", status.name, status.model, status.detail
    )
