"""Persistencia del lms-integration-service (schema dedicado `lms_sync`)."""
from libs.common.db import build_persistence

SCHEMA = "lms_sync"

engine, Base, SessionLocal = build_persistence(SCHEMA)


def get_session():
    """Dependencia FastAPI: entrega una sesion y la cierra al terminar la request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
