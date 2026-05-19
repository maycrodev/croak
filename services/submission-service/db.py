"""Persistencia del submission-service (schema dedicado `submission`)."""
from libs.common.db import build_persistence

SCHEMA = "submission"

engine, Base, SessionLocal = build_persistence(SCHEMA)


def get_session():
    """Dependencia FastAPI: entrega una sesion y la cierra al terminar la request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
