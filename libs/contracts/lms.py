"""Contratos de sincronizacion con el LMS (lms-integration-service, inciso IV).

Estos esquemas son el modelo LIMPIO interno. La traduccion al formato feo del
mainframe ocurre exclusivamente en services/lms-integration-service/acl.py.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class LmsSyncRequest(BaseModel):
    """Peticion interna para sincronizar una nota con el LMS."""

    submission_id: int
    student_id: int
    assignment_id: int
    grade: float  # nota normalizada 0-100


class LmsSyncRecord(BaseModel):
    """Estado de la sincronizacion de una nota con el mainframe."""

    submission_id: int
    student_id: int
    assignment_id: int
    grade: float
    mainframe_response_code: str
    status: Literal["synced", "failed"]
    synced_at: Optional[datetime] = None
    raw_request: str = ""
    raw_response: str = ""

    model_config = {"from_attributes": True}
