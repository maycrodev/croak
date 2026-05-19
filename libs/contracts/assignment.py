"""Contratos de tareas/assignments (assignment-service, CLAUDE.md incisos V y VII)."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class TestCase(BaseModel):
    """Un caso de prueba: se alimenta `stdin` al programa y se compara su salida
    contra `expected_stdout`. Otorga `points` si coincide."""

    stdin: str = ""
    expected_stdout: str
    points: float = 1.0


class MetricRule(BaseModel):
    """Regla de un criterio `metrics`: se evalua sobre el stdout de la corrida
    baseline (stdin vacio). Otorga `points` si coincide."""

    type: Literal["regex", "contains"]
    pattern: str
    points: float = 1.0


class GradingCriterion(BaseModel):
    """Criterio de calificacion definido por el profesor (inciso VII).

    Una assignment puede combinar criterios de ambos tipos:
      - `test_cases`: usa la lista `test_cases` (stdin -> stdout esperado).
      - `metrics`: usa la lista `rules` (regex/contains sobre el stdout baseline).
    """

    kind: Literal["test_cases", "metrics"] = "test_cases"
    name: str = "Pruebas automaticas"
    test_cases: list[TestCase] = []
    rules: list[MetricRule] = []


class AssignmentBase(BaseModel):
    title: str
    description: str = ""
    language: str = "python"
    deadline: datetime
    # 'best' = cuenta la mejor nota; 'last' = cuenta el ultimo intento (inciso VI, MVP3).
    attempt_policy: Literal["best", "last"] = "best"
    criteria: list[GradingCriterion] = []


class AssignmentCreate(AssignmentBase):
    professor_id: int


class AssignmentPublic(AssignmentBase):
    id: int
    professor_id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
