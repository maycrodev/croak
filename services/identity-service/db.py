"""Persistencia del identity-service (schema dedicado `identity`)."""
from libs.common.db import build_persistence

SCHEMA = "identity"

engine, Base, SessionLocal = build_persistence(SCHEMA)


def get_session():
    """Dependencia FastAPI: entrega una sesion y la cierra al terminar la request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
