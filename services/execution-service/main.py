"""execution-service — ejecuta el codigo del estudiante en el sandbox (inciso I).

Schema: `execution`. Puerto: 8004. Corre el codigo:
  - una vez por cada caso de prueba de la assignment (cada caso aporta su `stdin`);
  - una corrida BASELINE adicional con `stdin` vacio, cuyo stdout usan los
    criterios `metrics` del grading-service (ver ADR-006).
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
from sandbox import Runner, get_runner

SERVICE_NAME = "execution-service"
log = configure_logging(SERVICE_NAME, settings.log_level)

SUBMISSION_URL = os.environ.get("SUBMISSION_URL", "http://submission-service:8003")
ASSIGNMENT_URL = os.environ.get("ASSIGNMENT_URL", "http://assignment-service:8002")

BASELINE_INDEX = -1  # case_index que identifica la corrida baseline (stdin vacio)


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
    """Aplana, en orden estable, el stdin de cada caso de prueba.

    El grading-service aplana los casos en el MISMO orden para alinear indices.
    """
    stdins: list[str] = []
    for criterion in assignment.criteria:
        if criterion.kind == "test_cases":
            for case in criterion.test_cases:
                stdins.append(case.stdin)
    return stdins


def _run_case(runner: Runner, source_code: str, stdin: str,
              case_index: int, submission_id: int) -> CaseRun:
    """Ejecuta una corrida en una carpeta temporal aislada que se elimina al final."""
    workdir = tempfile.mkdtemp(prefix=f"croak_exec_{submission_id}_")
    try:
        outcome = runner.run(source_code, stdin, workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return CaseRun(
        case_index=case_index, stdin=stdin,
        stdout=outcome.stdout, stderr=outcome.stderr, exit_code=outcome.exit_code,
        duration_ms=outcome.duration_ms, timed_out=outcome.timed_out,
        status=outcome.status,
    )


@app.post("/executions", response_model=ExecutionResult, status_code=201)
def execute(req: ExecuteRequest, session: Session = Depends(get_session)):
    submission = _fetch_submission(req.submission_id)
    assignment = _fetch_assignment(submission.assignment_id)
    try:
        runner = get_runner(submission.language)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    # Una corrida por caso de prueba (cada una con su stdin).
    runs = [
        _run_case(runner, submission.source_code, stdin, index, req.submission_id)
        for index, stdin in enumerate(_collect_stdins(assignment))
    ]
    # Corrida baseline con stdin vacio: fuente de stdout para los criterios 'metrics'.
    baseline = _run_case(runner, submission.source_code, "", BASELINE_INDEX, req.submission_id)

    # Estado agregado: refleja los test_cases; si no hay, refleja la baseline.
    scored = runs if runs else [baseline]
    if any(r.status == "timeout" for r in scored):
        agg_status = "timeout"
    elif any(r.status == "runtime_error" for r in scored):
        agg_status = "runtime_error"
    else:
        agg_status = "success"

    all_runs = runs + [baseline]
    representative = runs[-1] if runs else baseline
    row = ExecutionResultRow(
        submission_id=req.submission_id,
        status=agg_status,
        stdout=representative.stdout,
        stderr=representative.stderr,
        exit_code=representative.exit_code,
        duration_ms=sum(r.duration_ms for r in all_runs),
        timed_out=any(r.timed_out for r in all_runs),
        runs=[r.model_dump() for r in runs],
        baseline_run=baseline.model_dump(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    record_event(
        service=SERVICE_NAME, action="completed", entity_type="execution",
        entity_id=str(row.id),
        payload={"submission_id": req.submission_id, "status": agg_status,
                 "test_case_runs": len(runs)},
    )
    log.info("ejecucion submission=%s result=%s status=%s test_cases=%s",
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
