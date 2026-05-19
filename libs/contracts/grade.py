"""Contratos de calificacion (grading-service, CLAUDE.md incisos I, VI, VII)."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class Grade(BaseModel):
    """Nota de un intento concreto.

    `score` es la nota final (0-100, ya con el tope aplicado). `breakdown` separa
    la contribucion de los criterios test_cases y metrics; `detail` lleva el
    desglose caso por caso.
    """

    id: Optional[int] = None
    submission_id: int
    assignment_id: int
    student_id: int
    score: float
    max_score: float = 100.0
    attempt_number: int = 1
    detail: dict = {}
    breakdown: dict = {}
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EffectiveGrade(BaseModel):
    """Nota efectiva de un estudiante en una assignment (inciso VI).

    Resultado de aplicar la politica de intentos (`best` / `last`) sobre todas
    las notas del par (assignment, estudiante).
    """

    assignment_id: int
    student_id: int
    effective_score: float
    source_submission_id: int
    source_attempt_number: int
    attempt_policy_used: Literal["best", "last"]
