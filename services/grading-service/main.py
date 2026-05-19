"""grading-service — aplica los criterios del profesor y persiste la nota (inciso I).

Schema: `grading`. Puerto: 8005. MVP1 soporta solo el criterio `test_cases`:
compara la salida real de cada corrida contra la salida esperada y suma puntos.
"""
from __future__ import annotations

import os
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
from libs.contracts.execution import ExecutionResult
from libs.contracts.grade import Grade
from libs.contracts.submission import SubmissionDetail

from db import SCHEMA, Base, engine, get_session
from models import GradeRow

SERVICE_NAME = "grading-service"
log = configure_logging(SERVICE_NAME, settings.log_level)

SUBMISSION_URL = os.environ.get("SUBMISSION_URL", "http://submission-service:8003")
ASSIGNMENT_URL = os.environ.get("ASSIGNMENT_URL", "http://assignment-service:8002")
EXECUTION_URL = os.environ.get("EXECUTION_URL", "http://execution-service:8004")


class GradeRequest(BaseModel):
    submission_id: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_schema(engine, SCHEMA, Base)
    log.info("grading-service iniciado")
    yield


app = FastAPI(title=SERVICE_NAME, lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


def _get(url: str) -> httpx.Response:
    with httpx.Client(timeout=15.0) as client:
        return client.get(url)


@app.post("/grades", response_model=Grade, status_code=201)
def grade(req: GradeRequest, session: Session = Depends(get_session)):
    sub_resp = _get(f"{SUBMISSION_URL}/submissions/{req.submission_id}")
    if sub_resp.status_code == 404:
        raise HTTPException(404, f"Submission {req.submission_id} no existe")
    sub_resp.raise_for_status()
    submission = SubmissionDetail.model_validate(sub_resp.json())

    asg_resp = _get(f"{ASSIGNMENT_URL}/assignments/{submission.assignment_id}")
    asg_resp.raise_for_status()
    assignment = AssignmentPublic.model_validate(asg_resp.json())

    exe_resp = _get(f"{EXECUTION_URL}/executions/{req.submission_id}")
    if exe_resp.status_code == 404:
        raise HTTPException(409, "La submission aun no tiene resultado de ejecucion")
    exe_resp.raise_for_status()
    execution = ExecutionResult.model_validate(exe_resp.json())

    # Aplana los casos en el MISMO orden que execution-service (indices alineados).
    flat_cases = []
    for criterion in assignment.criteria:
        if criterion.kind == "test_cases":
            for case in criterion.test_cases:
                flat_cases.append((criterion.name, case))

    score = 0.0
    max_score = 0.0
    case_results = []
    for index, (criterion_name, case) in enumerate(flat_cases):
        max_score += case.points
        actual = execution.runs[index].stdout.strip() if index < len(execution.runs) else ""
        expected = case.expected_stdout.strip()
        passed = actual == expected
        earned = case.points if passed else 0.0
        score += earned
        case_results.append({
            "criterion": criterion_name,
            "case_index": index,
            "passed": passed,
            "points_earned": earned,
            "points_possible": case.points,
            "expected_stdout": expected,
            "actual_stdout": actual,
        })

    detail = {
        "cases": case_results,
        "passed": sum(1 for c in case_results if c["passed"]),
        "total": len(case_results),
        "execution_status": execution.status,
    }
    row = GradeRow(
        submission_id=req.submission_id,
        assignment_id=submission.assignment_id,
        student_id=submission.student_id,
        score=score,
        max_score=max_score,
        detail=detail,
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    record_event(
        service=SERVICE_NAME, action="recorded", entity_type="grade",
        entity_id=str(row.id), actor_id=str(submission.student_id),
        payload={"submission_id": req.submission_id,
                 "score": score, "max_score": max_score},
    )
    log.info("nota submission=%s score=%s/%s", req.submission_id, score, max_score)
    return row


@app.get("/grades/{submission_id}", response_model=Grade)
def get_grade(submission_id: int, session: Session = Depends(get_session)):
    """Ultima nota registrada para una submission."""
    row = session.scalar(
        select(GradeRow)
        .where(GradeRow.submission_id == submission_id)
        .order_by(GradeRow.id.desc())
        .limit(1)
    )
    if not row:
        raise HTTPException(404, f"Sin nota para la submission {submission_id}")
    return row
