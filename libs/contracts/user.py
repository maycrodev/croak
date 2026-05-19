"""Contratos de usuario e identidad (identity-service, CLAUDE.md inciso I)."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Role = Literal["student", "professor", "admin"]


class UserCreate(BaseModel):
    """Alta de usuario."""

    email: str
    full_name: str
    role: Role = "student"
    password: str = Field(min_length=4)


class UserPublic(BaseModel):
    """Representacion publica de un usuario (sin password_hash)."""

    id: int
    email: str
    full_name: str
    role: Role
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    """Credenciales de inicio de sesion."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """Respuesta del login: JWT + datos del usuario autenticado."""

    access_token: str
    token_type: str = "bearer"
    user: UserPublic
