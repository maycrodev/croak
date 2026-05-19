"""Contratos de envios/submissions (submission-service, CLAUDE.md incisos I y VI)."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

SubmissionStatus = Literal["received", "executing", "executed", "graded", "rejected"]


class SubmissionCreate(BaseModel):
    """Envio de codigo por parte del estudiante."""

    assignment_id: int
    student_id: int
    language: str = "python"
    source_code: str


class SubmissionPublic(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    language: str
    attempt_number: int
    status: SubmissionStatus
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
