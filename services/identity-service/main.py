"""identity-service — usuarios, roles y emision de JWT (CLAUDE.md seccion 4).

Schema: `identity`. Puerto: 8001. Expone:
  GET  /health      estado del servicio
  POST /users       alta de usuario
  GET  /users       listado de usuarios
  POST /auth/login  valida credenciales y emite un JWT
  GET  /users/me    perfil del usuario autenticado (requiere Bearer token)
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from libs.common.config import settings
from libs.common.db import init_schema
from libs.common.jwt_utils import create_access_token, decode_token
from libs.common.logging_config import configure_logging
from libs.contracts.user import LoginRequest, TokenResponse, UserCreate, UserPublic

from db import Base, SCHEMA, engine, get_session
from models import User
from security import hash_password, verify_password

SERVICE_NAME = "identity-service"
log = configure_logging(SERVICE_NAME, settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_schema(engine, SCHEMA, Base)
    log.info("identity-service iniciado")
    yield


app = FastAPI(title=SERVICE_NAME, lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.post("/users", response_model=UserPublic, status_code=201)
def create_user(payload: UserCreate, session: Session = Depends(get_session)):
    """Crea un usuario.

    Nota (hackathon): endpoint abierto para permitir el bootstrap del seed. En
    produccion exigiria un token con rol admin.
    """
    if session.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=409, detail="El email ya esta registrado")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    log.info("usuario creado id=%s role=%s", user.id, user.role)
    return user


@app.get("/users", response_model=list[UserPublic])
def list_users(session: Session = Depends(get_session)):
    return list(session.scalars(select(User).order_by(User.id)))


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)):
    user = session.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    token = create_access_token(subject=user.id, role=user.role)
    log.info("login ok id=%s role=%s", user.id, user.role)
    return TokenResponse(access_token=token, user=UserPublic.model_validate(user))


def _current_user(authorization: str | None, session: Session) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Falta el token Bearer")
    try:
        claims = decode_token(authorization.split(" ", 1)[1])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token invalido o expirado")
    user = session.get(User, int(claims["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="El usuario del token no existe")
    return user


@app.get("/users/me", response_model=UserPublic)
def me(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
):
    return _current_user(authorization, session)
