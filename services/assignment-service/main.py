"""assignment-service — tareas: deadline y criterios de calificacion (incisos V, VII).

Schema: `assignment`. Puerto: 8002. En MVP1 los criterios soportados son casos de
prueba (`test_cases`); el enforcement del deadline llega en MVP2.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from libs.common.audit_client import record_event
from libs.common.config import settings
from libs.common.db import init_schema
from libs.common.logging_config import configure_logging
from libs.contracts.assignment import AssignmentCreate, AssignmentPublic

from db import SCHEMA, Base, engine, get_session
from models import Assignment

SERVICE_NAME = "assignment-service"
log = configure_logging(SERVICE_NAME, settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_schema(engine, SCHEMA, Base)
    log.info("assignment-service iniciado")
    yield


app = FastAPI(title=SERVICE_NAME, lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.post("/assignments", response_model=AssignmentPublic, status_code=201)
def create_assignment(payload: AssignmentCreate, session: Session = Depends(get_session)):
    assignment = Assignment(
        professor_id=payload.professor_id,
        title=payload.title,
        description=payload.description,
        language=payload.language,
        deadline=payload.deadline,
        attempt_policy=payload.attempt_policy,
        criteria=[c.model_dump() for c in payload.criteria],
    )
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    record_event(
        service=SERVICE_NAME, action="created", entity_type="assignment",
        entity_id=str(assignment.id), actor_id=str(payload.professor_id),
        payload={"title": assignment.title, "criteria_count": len(assignment.criteria)},
    )
    log.info("assignment creada id=%s '%s'", assignment.id, assignment.title)
    return assignment


@app.get("/assignments", response_model=list[AssignmentPublic])
def list_assignments(session: Session = Depends(get_session)):
    return list(session.scalars(select(Assignment).order_by(Assignment.id)))


@app.get("/assignments/{assignment_id}", response_model=AssignmentPublic)
def get_assignment(assignment_id: int, session: Session = Depends(get_session)):
    assignment = session.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment no encontrada")
    return assignment
