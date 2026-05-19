"""Contratos de deteccion de plagio (plagiarism-service, CLAUDE.md inciso III)."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class PlagiarismMatch(BaseModel):
    """Una coincidencia detectada, interna o del servicio externo (turnitin-mock)."""

    source: Literal["internal", "turnitin"]
    other_submission_id: Optional[int] = None
    similarity: float


class PlagiarismReport(BaseModel):
    """Reporte combinado: similitud interna (k-gram + winnowing) + externa."""

    id: Optional[int] = None
    submission_id: int
    internal_similarity: float = 0.0
    external_similarity: float = 0.0
    suspected: bool = False
    matches: list[PlagiarismMatch] = []
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
