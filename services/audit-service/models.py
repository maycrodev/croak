"""Modelo ORM del audit-service: bitacora append-only encadenada por hash."""
from sqlalchemy import JSON, Column, DateTime, Integer, String, func

from db import Base


class AuditEventRow(Base):
    """Un evento de auditoria. `prev_hash`/`hash` forman la cadena inmutable.

    No se expone UPDATE ni DELETE: la tabla es append-only por diseno (inciso II).
    """

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(100), nullable=False, index=True)
    actor_id = Column(String(100), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    prev_hash = Column(String(64), nullable=False)
    hash = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
