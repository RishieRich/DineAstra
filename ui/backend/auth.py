"""Demo authentication.

One seeded account, a salted hash in data/users.json, and a signed token.
The secret falls back to a published demo value so the app runs with no
.env at all; set DARPAN_SECRET to override it.

The failure message is deliberately identical for an unknown email and a
wrong password: the login screen does not tell an attacker which half was
right.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ui.backend import repository as repo

DEMO_SALT = "darpan-demo-2026"
SECRET = os.getenv("DARPAN_SECRET", "darpan-demo-secret-not-for-production")
ALGORITHM = "HS256"
TOKEN_TTL_HOURS = 12

INVALID_CREDENTIALS_MESSAGE = "That email and password do not match an account."
MISSING_TOKEN_MESSAGE = "Sign in to see this."

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return hashlib.sha256(f"{DEMO_SALT}:{password}".encode("utf-8")).hexdigest()


def authenticate(email: str, password: str) -> dict:
    """Return the user record, or raise 401 with the standard message."""
    user = repo.user_by_email(email)
    if user is None or not _password_matches(password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_MESSAGE,
        )
    return user


def _password_matches(password: str, expected_hash: str) -> bool:
    import hmac

    return hmac.compare_digest(hash_password(password), expected_hash)


def issue_token(user: dict) -> dict:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    payload = {
        "sub": user["email"],
        "name": user["name"],
        "role": user["role"],
        "exp": expires_at,
    }
    return {
        "token": jwt.encode(payload, SECRET, algorithm=ALGORITHM),
        "expires_at": expires_at.isoformat(),
        "user": {"email": user["email"], "name": user["name"], "role": user["role"]},
    }


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=MISSING_TOKEN_MESSAGE,
        ) from exc


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=MISSING_TOKEN_MESSAGE,
        )
    claims = decode_token(credentials.credentials)
    return {
        "email": claims.get("sub"),
        "name": claims.get("name"),
        "role": claims.get("role"),
    }
