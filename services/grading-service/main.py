"""grading-service — calificacion y nota efectiva (CLAUDE.md incisos I, VI, VII).

Schema: `grading`. Puerto: 8005.
  - Inciso VII: criterios `test_cases` (stdout esperado) y `metrics` (regex/contains
    sobre el stdout baseline). final_score = min(100, test_cases + metrics).
  - Inciso VI: nota efectiva (mejor/ultimo intento) y sync de ESA con el LMS.
"""
from __future__ import annotations

import os
import re
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
from libs.contracts.grade import EffectiveGrade, Grade
from libs.contracts.submission import SubmissionDetail

from db import SCHEMA, Base, engine, get_session
from models import GradeRow

SERVICE_NAME = "grading-service"
log = configure_logging(SERVICE_NAME, settings.log_level)

SUBMISSION_URL = os.environ.get("SUBMISSION_URL", "http://submission-service:8003")
ASSIGNMENT_URL = os.environ.get("ASSIGNMENT_URL", "http://assignment-service:8002")
EXECUTION_URL = os.environ.get("EXECUTION_URL", "http://execution-service:8004")
LMS_URL = os.environ.get("LMS_URL", "http://lms-integration-service:8007")

MAX_GRADE = 100.0


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


def _fetch_assignment(assignment_id: int) -> AssignmentPublic:
    resp = _get(f"{ASSIGNMENT_URL}/assignments/{assignment_id}")
    resp.raise_for_status()
    return AssignmentPublic.model_validate(resp.json())


def _evaluate_test_cases(assignment: AssignmentPublic, execution: ExecutionResult):
    """Criterios test_cases: compara el stdout real de cada corrida vs el esperado."""
    score = 0.0
    results = []
    index = 0
    for criterion in assignment.criteria:
        if criterion.kind != "test_cases":
            continue
        for case in criterion.test_cases:
            actual = (execution.runs[index].stdout.strip()
                      if index < len(execution.runs) else "")
            expected = case.expected_stdout.strip()
            passed = actual == expected
            earned = case.points if passed else 0.0
            score += earned
            results.append({
                "criterion": criterion.name, "case_index": index, "passed": passed,
                "points_earned": earned, "points_possible": case.points,
                "expected_stdout": expected, "actual_stdout": actual,
            })
            index += 1
    return score, results


def _evaluate_metrics(assignment: AssignmentPublic, execution: ExecutionResult):
    """Criterios metrics: aplica reglas regex/contains sobre el stdout baseline."""
    baseline = execution.baseline_run.stdout if execution.baseline_run else ""
    score = 0.0
    results = []
    for criterion in assignment.criteria:
        if criterion.kind != "metrics":
            continue
        for rule_index, rule in enumerate(criterion.rules):
            if rule.type == "regex":
                try:
                    matched = re.search(rule.pattern, baseline) is not None
                except re.error:
                    matched = False
            else:  # contains
                matched = rule.pattern in baseline
            earned = rule.points if matched else 0.0
            score += earned
            results.append({
                "criterion": criterion.name, "rule_index": rule_index,
                "type": rule.type, "pattern": rule.pattern, "matched": matched,
                "points_earned": earned, "points_possible": rule.points,
            })
    return score, results


def _compute_effective(grades: list[GradeRow], policy: str) -> GradeRow:
    """Nota efectiva segun la politica de intentos del profesor (inciso VI)."""
    if policy == "last":
        return max(grades, key=lambda g: g.attempt_number)
    # 'best': mayor score; en empate, el intento mas reciente.
    return max(grades, key=lambda g: (g.score, g.attempt_number))


@app.post("/grades", response_model=Grade, status_code=201)
def grade(req: GradeRequest, session: Session = Depends(get_session)):
    sub_resp = _get(f"{SUBMISSION_URL}/submissions/{req.submission_id}")
    if sub_resp.status_code == 404:
        raise HTTPException(404, f"Submission {req.submission_id} no existe")
    sub_resp.raise_for_status()
    submission = SubmissionDetail.model_validate(sub_resp.json())

    assignment = _fetch_assignment(submission.assignment_id)

    exe_resp = _get(f"{EXECUTION_URL}/executions/{req.submission_id}")
    if exe_resp.status_code == 404:
        raise HTTPException(409, "La submission aun no tiene resultado de ejecucion")
    exe_resp.raise_for_status()
    execution = ExecutionResult.model_validate(exe_resp.json())

    # --- Inciso VII: calificacion combinada test_cases + metrics ---
    tc_score, tc_results = _evaluate_test_cases(assignment, execution)
    m_score, m_results = _evaluate_metrics(assignment, execution)
    raw_score = tc_score + m_score
    final_score = min(MAX_GRADE, raw_score)
    breakdown = {
        "test_cases_score": tc_score,
        "metrics_score": m_score,
        "capped_at_100": raw_score > MAX_GRADE,
    }
    detail = {
        "test_cases": tc_results,
        "metrics": m_results,
        "execution_status": execution.status,
    }

    # Nota efectiva PREVIA (intentos anteriores), para detectar si cambia.
    prior = list(session.scalars(select(GradeRow).where(
        GradeRow.assignment_id == submission.assignment_id,
        GradeRow.student_id == submission.student_id,
    )))
    prior_effective = (
        _compute_effective(prior, assignment.attempt_policy).score if prior else None
    )

    row = GradeRow(
        submission_id=req.submission_id,
        assignment_id=submission.assignment_id,
        student_id=submission.student_id,
        score=final_score,
        max_score=MAX_GRADE,
        attempt_number=submission.attempt_number,
        detail=detail,
        breakdown=breakdown,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    record_event(
        service=SERVICE_NAME, action="recorded", entity_type="grade",
        entity_id=str(row.id), actor_id=str(submission.student_id),
        payload={"submission_id": req.submission_id, "score": final_score,
                 "test_cases_score": tc_score, "metrics_score": m_score},
    )
    log.info("nota submission=%s score=%s (tc=%s metrics=%s cap=%s)",
             req.submission_id, final_score, tc_score, m_score, breakdown["capped_at_100"])

    # --- Inciso VI: nota efectiva post-policy + sync de ESA con el LMS ---
    effective = _compute_effective(prior + [row], assignment.attempt_policy)
    unchanged = (prior_effective is not None
                 and abs(prior_effective - effective.score) < 1e-9)
    _sync_to_lms(effective, unchanged)
    return row


def _sync_to_lms(effective: GradeRow, unchanged: bool) -> None:
    """Inciso VI: sincroniza la nota EFECTIVA (no la del intento puntual) con el LMS.

    Best-effort: un fallo del LMS no revierte la nota local. El audit event incluye
    `effective_score`, `source_submission_id` y el flag `unchanged`.
    """
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.post(f"{LMS_URL}/lms/sync", json={
                "submission_id": effective.submission_id,
                "student_id": effective.student_id,
                "assignment_id": effective.assignment_id,
                "grade": effective.score,
            })
            resp.raise_for_status()
        data = resp.json()
        synced = data.get("status") == "synced"
        record_event(
            service=SERVICE_NAME,
            action="lms.synced" if synced else "lms.sync.failed",
            entity_type="grade", entity_id=str(effective.id),
            payload={"effective_score": effective.score,
                     "source_submission_id": effective.submission_id,
                     "unchanged": unchanged,
                     "code": data.get("mainframe_response_code")},
        )
        log.info("LMS sync efectiva=%s source_submission=%s unchanged=%s synced=%s",
                 effective.score, effective.submission_id, unchanged, synced)
    except httpx.HTTPError as exc:
        record_event(
            service=SERVICE_NAME, action="lms.sync.failed", entity_type="grade",
            entity_id=str(effective.id),
            payload={"effective_score": effective.score,
                     "source_submission_id": effective.submission_id,
                     "unchanged": unchanged, "error": str(exc)},
        )
        log.warning("LMS sync fallo (efectiva=%s): %s", effective.score, exc)


@app.get("/grades/effective", response_model=EffectiveGrade)
def get_effective(assignment_id: int, student_id: int,
                  session: Session = Depends(get_session)):
    """Nota efectiva de un estudiante en una assignment (inciso VI).

    Definida ANTES de /grades/{submission_id} para que 'effective' no se
    interprete como un id.
    """
    grades = list(session.scalars(select(GradeRow).where(
        GradeRow.assignment_id == assignment_id,
        GradeRow.student_id == student_id,
    )))
    if not grades:
        raise HTTPException(404, "Sin notas para ese (assignment, estudiante)")
    assignment = _fetch_assignment(assignment_id)
    winner = _compute_effective(grades, assignment.attempt_policy)
    return EffectiveGrade(
        assignment_id=assignment_id,
        student_id=student_id,
        effective_score=winner.score,
        source_submission_id=winner.submission_id,
        source_attempt_number=winner.attempt_number,
        attempt_policy_used=assignment.attempt_policy,
    )


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
