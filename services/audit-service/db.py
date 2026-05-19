"""Persistencia del audit-service (schema dedicado `audit`)."""
from libs.common.db import build_persistence

SCHEMA = "audit"

engine, Base, SessionLocal = build_persistence(SCHEMA)


def get_session():
    """Dependencia FastAPI: entrega una sesion y la cierra al terminar la request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
