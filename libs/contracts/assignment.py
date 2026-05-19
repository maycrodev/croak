"""Contratos de tareas/assignments (assignment-service, CLAUDE.md incisos V y VII)."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class GradingCriterion(BaseModel):
    """Criterio de calificacion definido por el profesor (inciso VII).

    `kind` distingue una prueba (test_case) de una metrica. `config` lleva los
    detalles especificos (entrada/salida esperada, umbral de la metrica, etc.).
    """

    kind: Literal["test_case", "metric"]
    name: str
    weight: float = 1.0
    config: dict = {}


class AssignmentBase(BaseModel):
    title: str
    description: str = ""
    language: str = "python"
    deadline: datetime
    # 'best' = cuenta la mejor nota; 'last' = cuenta el ultimo intento (inciso VI).
    attempt_policy: Literal["best", "last"] = "best"
    criteria: list[GradingCriterion] = []


class AssignmentCreate(AssignmentBase):
    professor_id: int


class AssignmentPublic(AssignmentBase):
    id: int
    professor_id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
