"""plagiarism-service — similitud interna + adaptador externo (CLAUDE.md inciso III).

Schema: `plagiarism`. Puerto: 8006.
  - Interna: k-gram + winnowing -> Jaccard contra otras submissions de la misma
    assignment.
  - Externa: via Adapter al proveedor simulado (turnitin-mock).
`flagged` queda en True si cualquiera de los dos puntajes alcanza el umbral.
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
from libs.contracts.plagiarism import PlagiarismMatch, PlagiarismReport
from libs.contracts.submission import SubmissionDetail

from db import SCHEMA, Base, engine, get_session
from fingerprint import fingerprint, jaccard
from models import PlagiarismReportRow
from turnitin_adapter import TurnitinAdapter

SERVICE_NAME = "plagiarism-service"
log = configure_logging(SERVICE_NAME, settings.log_level)

SUBMISSION_URL = os.environ.get("SUBMISSION_URL", "http://submission-service:8003")
TURNITIN_URL = os.environ.get("TURNITIN_URL", "http://turnitin-mock:8011")
THRESHOLD = float(os.environ.get("PLAGIARISM_THRESHOLD", "0.7"))


class CheckRequest(BaseModel):
    submission_id: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_schema(engine, SCHEMA, Base)
    log.info("plagiarism-service iniciado (umbral=%.2f)", THRESHOLD)
    yield


app = FastAPI(title=SERVICE_NAME, lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


def _get(url: str) -> httpx.Response:
    with httpx.Client(timeout=15.0) as client:
        return client.get(url)


@app.post("/plagiarism", response_model=PlagiarismReport, status_code=201)
def check(req: CheckRequest, session: Session = Depends(get_session)):
    sub_resp = _get(f"{SUBMISSION_URL}/submissions/{req.submission_id}")
    if sub_resp.status_code == 404:
        raise HTTPException(404, f"Submission {req.submission_id} no existe")
    sub_resp.raise_for_status()
    submission = SubmissionDetail.model_validate(sub_resp.json())

    # --- Similitud interna: contra otras submissions de la misma assignment ---
    peers_resp = _get(f"{SUBMISSION_URL}/submissions?assignment_id={submission.assignment_id}")
    peers_resp.raise_for_status()
    peers = [SubmissionDetail.model_validate(p) for p in peers_resp.json()]

    own_fingerprint = fingerprint(submission.source_code)
    matches: list[PlagiarismMatch] = []
    internal_score = 0.0
    for peer in peers:
        if peer.id == submission.id:
            continue
        similarity = jaccard(own_fingerprint, fingerprint(peer.source_code))
        internal_score = max(internal_score, similarity)
        if similarity > 0:
            matches.append(PlagiarismMatch(
                source="internal", other_submission_id=peer.id,
                similarity=round(similarity, 4),
            ))

    # --- Similitud externa: via Adapter al proveedor (turnitin-mock) ---
    external = TurnitinAdapter(TURNITIN_URL).check(submission.source_code)
    matches.extend(external.matches)

    internal_score = round(internal_score, 4)
    external_score = round(external.score, 4)
    flagged = internal_score >= THRESHOLD or external_score >= THRESHOLD

    row = PlagiarismReportRow(
        submission_id=req.submission_id,
        internal_score=internal_score,
        external_score=external_score,
        flagged=flagged,
        threshold=THRESHOLD,
        matches=[m.model_dump() for m in matches],
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    record_event(
        service=SERVICE_NAME, action="checked", entity_type="plagiarism_report",
        entity_id=str(row.id),
        payload={"submission_id": req.submission_id,
                 "internal_score": internal_score,
                 "external_score": external_score, "flagged": flagged},
    )
    log.info("plagio submission=%s interno=%.3f externo=%.3f flagged=%s",
             req.submission_id, internal_score, external_score, flagged)
    return row


@app.get("/plagiarism/{submission_id}", response_model=PlagiarismReport)
def get_report(submission_id: int, session: Session = Depends(get_session)):
    """Ultimo reporte de plagio de una submission."""
    row = session.scalar(
        select(PlagiarismReportRow)
        .where(PlagiarismReportRow.submission_id == submission_id)
        .order_by(PlagiarismReportRow.id.desc())
        .limit(1)
    )
    if not row:
        raise HTTPException(404, f"Sin reporte de plagio para la submission {submission_id}")
    return row
