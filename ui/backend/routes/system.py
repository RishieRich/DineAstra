"""System routes: health, auth, connections, and the metric catalogue."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from agents import registry
from ui.backend import auth
from ui.backend import repository as repo

router = APIRouter(prefix="/api", tags=["system"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


@router.get("/health")
def health() -> dict:
    first, last = repo.property_date_bounds()
    return {
        "status": "ok",
        "service": "darpan-api",
        "version": "0.1.0",
        "mode": "sample data",
        "today": repo.anchor_date().isoformat(),
        "data_window": {"first": first, "last": last},
        "metric_count": len(registry.METRICS),
    }


@router.post("/auth/login")
def login(payload: LoginRequest) -> dict:
    user = auth.authenticate(payload.email, payload.password)
    return auth.issue_token(user)


@router.get("/auth/me")
def me(user: dict = Depends(auth.current_user)) -> dict:
    return user


@router.get("/system/connections")
def connections(user: dict = Depends(auth.current_user)) -> dict:
    return {
        "connections": repo.connections_all(),
        "any_connected": any(
            c["status"] == "connected" for c in repo.connections_all()
        ),
        "note": "Darpan runs on generated sample data. Nothing is connected.",
    }


@router.get("/system/metrics")
def metrics(user: dict = Depends(auth.current_user)) -> dict:
    return {"metrics": registry.catalogue(), "count": len(registry.METRICS)}
