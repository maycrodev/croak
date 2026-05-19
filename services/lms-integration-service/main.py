"""lms-integration-service — Anti-Corruption Layer hacia el LMS mainframe (inciso IV).

Schema: `lms_sync`. Puerto: 8007. Recibe una nota en el modelo limpio interno,
delega la traduccion al/del formato del mainframe en `acl.py`, hace un unico POST
al mainframe-mock y persiste el estado de la sincronizacion.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from libs.common.audit_client import record_event
from libs.common.config import settings
from libs.common.db import init_schema
from libs.common.logging_config import configure_logging
from libs.contracts.lms import LmsSyncRecord, LmsSyncRequest

from acl import GradeEvent, from_mainframe, to_mainframe
from db import SCHEMA, Base, engine, get_session
from models import LmsSyncRow

SERVICE_NAME = "lms-integration-service"
log = configure_logging(SERVICE_NAME, settings.log_level)

MAINFRAME_URL = os.environ.get("MAINFRAME_URL", "http://lms-mainframe-mock:8012")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_schema(engine, SCHEMA, Base)
    log.info("lms-integration-service iniciado")
    yield


app = FastAPI(title=SERVICE_NAME, lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.post("/lms/sync", response_model=LmsSyncRecord)
def sync(payload: LmsSyncRequest, session: Session = Depends(get_session)):
    """Sincroniza la nota de una submission con el mainframe LMS.

    Un solo intento (sin reintentos automaticos en MVP2). El resultado, exitoso
    o no, queda persistido y consultable via GET /lms/sync/{submission_id}.
    """
    # 1) ACL: modelo limpio -> registro feo del mainframe.
    record = to_mainframe(GradeEvent(
        student_id=payload.student_id,
        assignment_id=payload.assignment_id,
        grade=payload.grade,
    ))

    record_event(
        service=SERVICE_NAME, action="sync.attempt", entity_type="lms_sync",
        entity_id=str(payload.submission_id),
        payload={"submission_id": payload.submission_id, "grade": payload.grade},
    )

    # 2) Unico POST al mainframe.
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{MAINFRAME_URL}/COBOL/GRADESYNC",
                content=record,
                headers={"Content-Type": "text/plain"},
            )
            resp.raise_for_status()
            response_dict = resp.json()
    except httpx.HTTPError as exc:
        response_dict = {"code": "0099", "message": f"NO RESPONSE FROM MAINFRAME: {exc}"}

    # 3) ACL: respuesta fea -> modelo limpio.
    result = from_mainframe(response_dict)

    # 4) Persistir (upsert por submission_id).
    row = session.get(LmsSyncRow, payload.submission_id)
    if row is None:
        row = LmsSyncRow(submission_id=payload.submission_id)
        session.add(row)
    row.student_id = payload.student_id
    row.assignment_id = payload.assignment_id
    row.grade = payload.grade
    row.mainframe_response_code = result.code
    row.status = result.status
    row.synced_at = dt.datetime.now(dt.timezone.utc)
    row.raw_request = record.decode("ascii")
    row.raw_response = json.dumps(response_dict, ensure_ascii=False)
    session.commit()
    session.refresh(row)

    record_event(
        service=SERVICE_NAME, action="sync.result", entity_type="lms_sync",
        entity_id=str(payload.submission_id),
        payload={"submission_id": payload.submission_id,
                 "status": result.status, "code": result.code},
    )
    log.info("sync submission=%s status=%s code=%s",
             payload.submission_id, result.status, result.code)
    return row


@app.get("/lms/sync/{submission_id}", response_model=LmsSyncRecord)
def get_sync(submission_id: int, session: Session = Depends(get_session)):
    """Estado actual de la sincronizacion LMS de una submission."""
    row = session.get(LmsSyncRow, submission_id)
    if not row:
        raise HTTPException(404, f"Sin sincronizacion LMS para la submission {submission_id}")
    return row
