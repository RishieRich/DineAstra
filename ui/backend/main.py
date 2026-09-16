"""DineAstra backend entrypoint.

Run from the repo root:

    uvicorn ui.backend.main:app --port 8000 --reload
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from agents import narrator
from ui.backend import store
from ui.backend.routes import ask, banquet, brain, data, operations, overview, system

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

# httpx logs every request line at INFO, and the Gemini endpoint carries the
# API key as a query parameter. Nothing is worth putting a live key in a log
# file, so httpx only speaks up here when something actually goes wrong.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

app = FastAPI(title="DineAstra API", version="0.2.0")

# On Vercel the frontend and the API are served from one origin, so CORS is
# only needed for local development, where Vite runs on its own port.
_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def bind_workspace(request: Request, call_next):
    """Give each visitor their own sandbox of uploaded data.

    A shared demo link is opened by people who do not know each other. The
    browser generates a workspace id and sends it on every call; everything a
    visitor loads, uploads or clears is scoped to it, so one person clearing
    their data cannot empty the screen someone else is presenting from.

    An absent or malformed id falls back to the shared default rather than
    failing the request -- a demo should still work from curl.
    """
    workspace = store.valid_workspace(request.headers.get("X-Workspace-Id"))
    token = store.set_workspace(workspace or store.DEFAULT_WORKSPACE)
    try:
        return await call_next(request)
    finally:
        store.reset_workspace(token)

app.include_router(system.router)
app.include_router(overview.router)
app.include_router(banquet.router)
app.include_router(operations.router)
app.include_router(ask.router)
app.include_router(brain.router)
app.include_router(data.router)


@app.on_event("startup")
def resolve_provider_at_startup() -> None:
    """Rule VIII: validate the configured model before serving, not during a
    question. A bad model id logs the ids that are available and falls through
    to the next provider; the app serves every screen either way."""
    status = narrator.startup()
    logging.getLogger("darpan").info(
        "Answering through %s (%s): %s", status.name, status.model, status.detail
    )
