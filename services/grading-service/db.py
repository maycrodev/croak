"""Persistencia del grading-service (schema dedicado `grading`)."""
from libs.common.db import build_persistence

SCHEMA = "grading"

engine, Base, SessionLocal = build_persistence(SCHEMA)


def get_session():
    """Dependencia FastAPI: entrega una sesion y la cierra al terminar la request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
