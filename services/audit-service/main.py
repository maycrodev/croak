"""audit-service — bitacora append-only encadenada por hash (inciso II + contexto b).

Schema: `audit`. Puerto: 8008.
  POST /audit/events         registra un evento (encadenado por hash)
  GET  /audit/events         lista la bitacora (filtros opcionales)
  GET  /audit/events/verify  verifica la integridad de toda la cadena (admin/professor)
  GET  /audit/export/annual  export anual inmutable para la entidad estatal (admin)

La cadena hace la bitacora inmutable: cada evento guarda el hash del anterior;
alterar un registro rompe la cadena y `/audit/events/verify` lo detecta.
"""
from __future__ import annotations

import hashlib
import json
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
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


def _canonical_json(data) -> str:
    """JSON canonico: claves ordenadas y sin espacios. Hace el hash reproducible."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def _event_core(service: str, action: str, entity_type: str, entity_id: str,
                actor_id: Optional[str], payload: dict) -> dict:
    """Contenido del evento que entra al hash.

    Se construye IGUAL al escribir y al verificar, para que la verificacion
    recalcule exactamente el mismo hash.
    """
    return {
        "service": service, "action": action, "entity_type": entity_type,
        "entity_id": entity_id, "actor_id": actor_id, "payload": payload,
    }


def _compute_hash(prev_hash: str, event_core: dict) -> str:
    """hash = sha256(prev_hash || canonical_json(contenido del evento))."""
    return hashlib.sha256(
        (prev_hash + _canonical_json(event_core)).encode("utf-8")
    ).hexdigest()


def _require_role(*allowed_roles: str):
    """Dependencia: exige que el gateway haya propagado un rol permitido.

    El gateway valida el JWT y propaga el rol verificado en `X-User-Role`.
    """
    def _checker(x_user_role: Optional[str] = Header(default=None)):
        if x_user_role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Operacion restringida al rol: {', '.join(allowed_roles)}",
            )
        return x_user_role
    return _checker


def _verify_chain(events: list[AuditEventRow], expect_genesis: bool = True) -> dict:
    """Recalcula y valida la cadena de hashes de una lista de eventos (orden por id).

    `expect_genesis=False` valida un sub-rango (p. ej. un anio): su primer evento
    NO encadena con el hash genesis sino con el evento previo del rango.
    """
    if not events:
        return {"intact": True, "count": 0, "genesis_ok": True,
                "head_hash": GENESIS_HASH, "first_break_id": None}

    intact = True
    first_break_id: Optional[int] = None
    genesis_ok = events[0].prev_hash == GENESIS_HASH
    expected_prev = GENESIS_HASH if expect_genesis else events[0].prev_hash

    for ev in events:
        core = _event_core(ev.service, ev.action, ev.entity_type,
                           ev.entity_id, ev.actor_id, ev.payload)
        recomputed = _compute_hash(ev.prev_hash, core)
        if ev.prev_hash != expected_prev or ev.hash != recomputed:
            intact = False
            if first_break_id is None:
                first_break_id = ev.id
        expected_prev = ev.hash

    if expect_genesis and not genesis_ok:
        intact = False

    return {"intact": intact, "count": len(events), "genesis_ok": genesis_ok,
            "head_hash": events[-1].hash, "first_break_id": first_break_id}


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
    core = _event_core(payload.service, payload.action, payload.entity_type,
                       payload.entity_id, payload.actor_id, payload.payload)
    with _chain_lock:
        last = session.scalar(
            select(AuditEventRow).order_by(AuditEventRow.id.desc()).limit(1)
        )
        prev_hash = last.hash if last else GENESIS_HASH
        row = AuditEventRow(
            **core, prev_hash=prev_hash, hash=_compute_hash(prev_hash, core),
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


@app.get("/audit/events/verify")
def verify_chain(
    _role: str = Depends(_require_role("admin", "professor")),
    session: Session = Depends(get_session),
):
    """Verifica la integridad de TODA la bitacora recalculando la cadena de hashes."""
    events = list(session.scalars(select(AuditEventRow).order_by(AuditEventRow.id)))
    result = _verify_chain(events, expect_genesis=True)
    return {
        "intact": result["intact"],
        "total_events": result["count"],
        "genesis_ok": result["genesis_ok"],
        "head_hash": result["head_hash"],
        "first_break_id": result["first_break_id"],
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/audit/export/annual")
def export_annual(
    year: int = Query(..., ge=1970, le=9998),
    _role: str = Depends(_require_role("admin")),
    session: Session = Depends(get_session),
):
    """Export anual inmutable de auditoria para la entidad estatal (contexto b).

    Devuelve metadata + todos los eventos del anio UTC + un `export_seal` (sha256
    del documento) que permite a la entidad detectar alteraciones del archivo.
    """
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    events = list(session.scalars(
        select(AuditEventRow)
        .where(AuditEventRow.created_at >= start, AuditEventRow.created_at < end)
        .order_by(AuditEventRow.id)
    ))

    integrity = _verify_chain(events, expect_genesis=False)
    document = {
        "metadata": {
            "year": year,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "event_count": len(events),
            "first_event_id": events[0].id if events else None,
            "last_event_id": events[-1].id if events else None,
            "first_hash": events[0].hash if events else None,
            "last_hash": events[-1].hash if events else None,
            "integrity": {
                "intact": integrity["intact"],
                "verified_range": (f"[{events[0].id}, {events[-1].id}]"
                                   if events else "[]"),
            },
        },
        "events": [AuditEvent.model_validate(e).model_dump(mode="json") for e in events],
    }
    # export_seal = sha256 del JSON canonico del documento SIN el propio sello.
    document["export_seal"] = hashlib.sha256(
        _canonical_json(document).encode("utf-8")
    ).hexdigest()
    log.info("export anual year=%s eventos=%s intact=%s",
             year, len(events), integrity["intact"])
    return document
