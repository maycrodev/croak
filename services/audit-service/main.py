"""audit-service — bitacora append-only encadenada por hash (CLAUDE.md inciso II).

Schema: `audit`. Puerto: 8008. Cada evento guarda el `hash` del evento anterior
(`prev_hash`); alterar cualquier registro rompe la cadena, lo que hace la bitacora
verificable e inmutable para la auditoria estatal anual (la verificacion formal
`/verify` se entrega en MVP4).
"""
from __future__ import annotations

import hashlib
import json
import threading
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from libs.common.config import settings
from libs.common.db import init_schema
from libs.common.logging_config import configure_logging
from libs.contracts.audit import AuditEvent, AuditEventIn

from db import SCHEMA, Base, engine, get_session
from models import AuditEventRow

SERVICE_NAME = "audit-service"
GENESIS_HASH = "0" * 64
log = configure_logging(SERVICE_NAME, settings.log_level)

# Serializa la insercion para que la cadena de hashes no se corrompa con requests
# concurrentes (FastAPI sirve los endpoints sync en un threadpool).
_chain_lock = threading.Lock()


def _canonical_json(data: dict) -> str:
    """JSON canonico: claves ordenadas, sin espacios. Hace el hash reproducible."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def _compute_hash(prev_hash: str, event_core: dict) -> str:
    """hash = sha256(prev_hash || canonical_json(contenido del evento)).

    Se encadena el evento COMPLETO (service/action/entity/payload), no solo el
    payload de negocio: asi cualquier alteracion rompe la cadena.
    """
    return hashlib.sha256(
        (prev_hash + _canonical_json(event_core)).encode("utf-8")
    ).hexdigest()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_schema(engine, SCHEMA, Base)
    log.info("audit-service iniciado")
    yield


app = FastAPI(title=SERVICE_NAME, lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.post("/audit/events", response_model=AuditEvent, status_code=201)
def create_event(payload: AuditEventIn, session: Session = Depends(get_session)):
    event_core = {
        "service": payload.service,
        "action": payload.action,
        "entity_type": payload.entity_type,
        "entity_id": payload.entity_id,
        "actor_id": payload.actor_id,
        "payload": payload.payload,
    }
    with _chain_lock:
        last = session.scalar(
            select(AuditEventRow).order_by(AuditEventRow.id.desc()).limit(1)
        )
        prev_hash = last.hash if last else GENESIS_HASH
        row = AuditEventRow(
            **event_core,
            prev_hash=prev_hash,
            hash=_compute_hash(prev_hash, event_core),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
    log.info("evento registrado id=%s %s/%s hash=%s",
             row.id, row.service, row.action, row.hash[:12])
    return row


@app.get("/audit/events", response_model=list[AuditEvent])
def list_events(
    entity_type: Optional[str] = Query(default=None),
    entity_id: Optional[str] = Query(default=None),
    service: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
):
    """Lista la bitacora en orden cronologico, con filtros opcionales."""
    stmt = select(AuditEventRow).order_by(AuditEventRow.id)
    if entity_type:
        stmt = stmt.where(AuditEventRow.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditEventRow.entity_id == entity_id)
    if service:
        stmt = stmt.where(AuditEventRow.service == service)
    return list(session.scalars(stmt))
