"""Contrato de calificacion persistente (grading-service, CLAUDE.md inciso I)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Grade(BaseModel):
    """Nota resultante de aplicar los criterios del profesor a un envio."""

    id: Optional[int] = None
    submission_id: int
    assignment_id: int
    student_id: int
    score: float
    max_score: float = 100.0
    # Desglose por criterio: {nombre_criterio: puntaje}.
    detail: dict = {}
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
