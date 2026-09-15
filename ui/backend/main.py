"""Darpan backend entrypoint.

Run from the repo root:

    uvicorn ui.backend.main:app --port 8000 --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ui.backend.routes import banquet, operations, overview, system

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
