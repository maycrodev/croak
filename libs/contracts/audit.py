"""Contratos de auditoria (audit-service, CLAUDE.md inciso II y contexto b).

El audit-service mantiene una bitacora append-only encadenada por hash: cada
evento guarda el `hash` del evento anterior (`prev_hash`), lo que hace el registro
inmutable y verificable para la auditoria estatal anual.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuditEventIn(BaseModel):
    """Evento que un servicio envia al audit-service."""

    service: str
    action: str
    entity_type: str
    entity_id: str
    actor_id: Optional[str] = None
    payload: dict = {}


class AuditEvent(AuditEventIn):
    """Evento ya persistido, con su lugar en la cadena de hashes."""

    id: int
    prev_hash: str
    hash: str
    created_at: datetime

    model_config = {"from_attributes": True}
