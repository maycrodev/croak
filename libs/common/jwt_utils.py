"""Emision y validacion de JWT HS256 (auth simple del hackathon, ver CLAUDE.md 3)."""
from __future__ import annotations

import datetime as dt
from typing import Any

import jwt

from .config import settings


def create_access_token(subject: str, role: str, extra: dict[str, Any] | None = None) -> str:
    """Emite un JWT firmado con HS256. `subject` es normalmente el id de usuario."""
    now = dt.datetime.now(dt.timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.jwt_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Valida firma y expiracion. Lanza jwt.PyJWTError si el token es invalido."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
