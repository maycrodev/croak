"""Capa de persistencia compartida (SQLAlchemy 2.x + PostgreSQL).

Cada servicio usa su propio schema (database-per-service logico, ver CLAUDE.md
secciones 3 y 4). No hay claves foraneas entre schemas: las relaciones cruzadas
se resuelven por ID + llamada HTTP.
"""
from __future__ import annotations

import logging
import time

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

log = logging.getLogger("croak.db")


def build_persistence(schema: str):
    """Crea el engine, la Base declarativa y la fabrica de sesiones de un schema."""
    engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    base = declarative_base(metadata=MetaData(schema=schema))
    session_local = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False, future=True
    )
    return engine, base, session_local


def init_schema(engine, schema: str, base, retries: int = 15, delay: float = 2.0) -> None:
    """Espera a Postgres, crea el schema si no existe y materializa las tablas.

    El reintento cubre el arranque en frio de `docker compose up`, cuando Postgres
    todavia no acepta conexiones.
    """
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with engine.begin() as conn:
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
            base.metadata.create_all(engine)
            log.info("schema '%s' listo (intento %d)", schema, attempt)
            return
        except OperationalError as exc:  # Postgres aun no acepta conexiones
            last_error = exc
            log.warning(
                "Postgres no disponible (intento %d/%d), reintentando en %.0fs...",
                attempt, retries, delay,
            )
            time.sleep(delay)
    raise RuntimeError(f"No se pudo inicializar el schema '{schema}'") from last_error
