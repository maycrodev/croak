"""submission-service — carga de codigo y orquestacion de la evaluacion.

Schema: `submission`. Puerto: 8003. Al recibir un POST /submissions encadena de
forma sincrona: ejecucion -> calificacion -> plagio. Cada paso de la cadena deja
un evento en la bitacora de auditoria (CLAUDE.md incisos I y II).
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from libs.common.audit_client import record_event
from libs.common.config import settings
from libs.common.db import init_schema
from libs.common.logging_config import configure_logging
from libs.contracts.submission import SubmissionCreate, SubmissionDetail

from db import SCHEMA, Base, engine, get_session
from models import Submission

SERVICE_NAME = "submission-service"
log = configure_logging(SERVICE_NAME, settings.log_level)

EXECUTION_URL = os.environ.get("EXECUTION_URL", "http://execution-service:8004")
GRADING_URL = os.environ.get("GRADING_URL", "http://grading-service:8005")
PLAGIARISM_URL = os.environ.get("PLAGIARISM_URL", "http://plagiarism-service:8006")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_schema(engine, SCHEMA, Base)
    log.info("submission-service iniciado")
    yield


app = FastAPI(title=SERVICE_NAME, lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


def _set_status(session: Session, submission: Submission,
                status: str, failure_reason: Optional[str] = None) -> None:
    submission.status = status
    submission.failure_reason = failure_reason
    session.commit()


def _orchestrate(session: Session, submission: Submission) -> None:
    """Cadena sincrona execution -> grading -> plagio.

    execution y grading son criticos: si fallan, la submission queda en `failed`.
    El chequeo de plagio es best-effort y no invalida una nota ya calculada.
    """
    sub_id = submission.id
    try:
        _set_status(session, submission, "executing")
        with httpx.Client(timeout=120.0) as client:
            client.post(f"{EXECUTION_URL}/executions",
                        json={"submission_id": sub_id}).raise_for_status()
        _set_status(session, submission, "executed")

        with httpx.Client(timeout=60.0) as client:
            client.post(f"{GRADING_URL}/grades",
                        json={"submission_id": sub_id}).raise_for_status()
        _set_status(session, submission, "graded")
    except httpx.HTTPError as exc:
        reason = f"Fallo en la cadena de evaluacion: {exc}"
        _set_status(session, submission, "failed", reason)
        record_event(
            service=SERVICE_NAME, action="failed", entity_type="submission",
            entity_id=str(sub_id), actor_id=str(submission.student_id),
            payload={"reason": reason},
        )
        log.warning("submission id=%s fallo: %s", sub_id, exc)
        return

    try:
        with httpx.Client(timeout=60.0) as client:
            client.post(f"{PLAGIARISM_URL}/plagiarism",
                        json={"submission_id": sub_id}).raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("submission id=%s: chequeo de plagio fallo (no critico): %s",
                    sub_id, exc)

    record_event(
        service=SERVICE_NAME, action="completed", entity_type="submission",
        entity_id=str(sub_id), actor_id=str(submission.student_id),
        payload={"final_status": submission.status},
    )


@app.post("/submissions", response_model=SubmissionDetail, status_code=201)
def create_submission(payload: SubmissionCreate, session: Session = Depends(get_session)):
    # Numero de intento N+1 para este (assignment, estudiante).
    previous = session.scalar(
        select(func.count(Submission.id)).where(
            Submission.assignment_id == payload.assignment_id,
            Submission.student_id == payload.student_id,
        )
    )
    submission = Submission(
        assignment_id=payload.assignment_id,
        student_id=payload.student_id,
        language=payload.language,
        source_code=payload.source_code,
        attempt_number=(previous or 0) + 1,
        status="received",
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)
    record_event(
        service=SERVICE_NAME, action="created", entity_type="submission",
        entity_id=str(submission.id), actor_id=str(submission.student_id),
        payload={"assignment_id": submission.assignment_id,
                 "attempt_number": submission.attempt_number},
    )
    log.info("submission creada id=%s intento=%s", submission.id, submission.attempt_number)

    _orchestrate(session, submission)
    session.refresh(submission)
    return submission


@app.get("/submissions/{submission_id}", response_model=SubmissionDetail)
def get_submission(submission_id: int, session: Session = Depends(get_session)):
    submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission no encontrada")
    return submission


@app.get("/submissions", response_model=list[SubmissionDetail])
def list_submissions(
    assignment_id: Optional[int] = Query(default=None),
    student_id: Optional[int] = Query(default=None),
    session: Session = Depends(get_session),
):
    stmt = select(Submission).order_by(Submission.id)
    if assignment_id is not None:
        stmt = stmt.where(Submission.assignment_id == assignment_id)
    if student_id is not None:
        stmt = stmt.where(Submission.student_id == student_id)
    return list(session.scalars(stmt))
