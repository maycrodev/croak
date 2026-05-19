"""execution-service — ejecuta el codigo del estudiante en el sandbox (inciso I).

Schema: `execution`. Puerto: 8004. Corre el codigo una vez por cada caso de prueba
de la assignment (cada caso aporta su `stdin`). Persiste un ExecutionResult con el
detalle por corrida y emite un evento de auditoria.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from libs.common.audit_client import record_event
from libs.common.config import settings
from libs.common.db import init_schema
from libs.common.logging_config import configure_logging
from libs.contracts.assignment import AssignmentPublic
from libs.contracts.execution import CaseRun, ExecutionResult
from libs.contracts.submission import SubmissionDetail

from db import SCHEMA, Base, engine, get_session
from models import ExecutionResultRow
from sandbox import get_runner

SERVICE_NAME = "execution-service"
log = configure_logging(SERVICE_NAME, settings.log_level)

SUBMISSION_URL = os.environ.get("SUBMISSION_URL", "http://submission-service:8003")
ASSIGNMENT_URL = os.environ.get("ASSIGNMENT_URL", "http://assignment-service:8002")


class ExecuteRequest(BaseModel):
    submission_id: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_schema(engine, SCHEMA, Base)
    log.info("execution-service iniciado")
    yield


app = FastAPI(title=SERVICE_NAME, lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


def _fetch_submission(submission_id: int) -> SubmissionDetail:
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(f"{SUBMISSION_URL}/submissions/{submission_id}")
    if resp.status_code == 404:
        raise HTTPException(404, f"Submission {submission_id} no existe")
    resp.raise_for_status()
    return SubmissionDetail.model_validate(resp.json())


def _fetch_assignment(assignment_id: int) -> AssignmentPublic:
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(f"{ASSIGNMENT_URL}/assignments/{assignment_id}")
    resp.raise_for_status()
    return AssignmentPublic.model_validate(resp.json())


def _collect_stdins(assignment: AssignmentPublic) -> list[str]:
    """Aplana, en orden estable, el stdin de cada caso de prueba de la assignment.

    El grading-service aplana los casos en el MISMO orden para alinear indices.
    """
    stdins: list[str] = []
    for criterion in assignment.criteria:
        if criterion.kind == "test_cases":
            for case in criterion.test_cases:
                stdins.append(case.stdin)
    return stdins


@app.post("/executions", response_model=ExecutionResult, status_code=201)
def execute(req: ExecuteRequest, session: Session = Depends(get_session)):
    submission = _fetch_submission(req.submission_id)
    assignment = _fetch_assignment(submission.assignment_id)
    try:
        runner = get_runner(submission.language)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    stdins = _collect_stdins(assignment) or [""]  # sin casos: una sola corrida

    runs: list[CaseRun] = []
    for index, stdin in enumerate(stdins):
        workdir = tempfile.mkdtemp(prefix=f"croak_exec_{req.submission_id}_")
        try:
            outcome = runner.run(submission.source_code, stdin, workdir)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        runs.append(CaseRun(
            case_index=index, stdin=stdin,
            stdout=outcome.stdout, stderr=outcome.stderr,
            exit_code=outcome.exit_code, duration_ms=outcome.duration_ms,
            timed_out=outcome.timed_out, status=outcome.status,
        ))

    # Estado agregado: el "peor" resultado entre todas las corridas.
    if any(r.status == "timeout" for r in runs):
        agg_status = "timeout"
    elif any(r.status == "runtime_error" for r in runs):
        agg_status = "runtime_error"
    else:
        agg_status = "success"
    last = runs[-1]

    row = ExecutionResultRow(
        submission_id=req.submission_id,
        status=agg_status,
        stdout=last.stdout,
        stderr=last.stderr,
        exit_code=last.exit_code,
        duration_ms=sum(r.duration_ms for r in runs),
        timed_out=any(r.timed_out for r in runs),
        runs=[r.model_dump() for r in runs],
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    record_event(
        service=SERVICE_NAME, action="completed", entity_type="execution",
        entity_id=str(row.id),
        payload={"submission_id": req.submission_id, "status": agg_status,
                 "runs": len(runs)},
    )
    log.info("ejecucion submission=%s result=%s status=%s corridas=%s",
             req.submission_id, row.id, agg_status, len(runs))
    return row


@app.get("/executions/{submission_id}", response_model=ExecutionResult)
def get_result(submission_id: int, session: Session = Depends(get_session)):
    """Ultimo resultado de ejecucion de una submission."""
    row = session.scalar(
        select(ExecutionResultRow)
        .where(ExecutionResultRow.submission_id == submission_id)
        .order_by(ExecutionResultRow.id.desc())
        .limit(1)
    )
    if not row:
        raise HTTPException(404, f"Sin ejecucion para la submission {submission_id}")
    return row
