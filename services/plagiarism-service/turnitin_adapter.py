"""Adapter hacia el servicio externo de plagio (patron Adapter, CLAUDE.md 6).

Aisla el formato del proveedor externo: migrar de `turnitin-mock` a un TurnItIn
real solo deberia tocar este archivo, no el plagiarism-service.
"""
from __future__ import annotations

import logging

import httpx

from libs.contracts.plagiarism import PlagiarismMatch

log = logging.getLogger("croak.turnitin-adapter")


class ExternalCheck:
    """Resultado del proveedor externo, ya traducido al modelo interno."""

    def __init__(self, score: float, matches: list[PlagiarismMatch]):
        self.score = score
        self.matches = matches


class TurnitinAdapter:
    """Traduce el modelo interno <-> la API del proveedor externo de plagio."""

    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")

    def check(self, source_code: str) -> ExternalCheck:
        """Consulta al proveedor y traduce su respuesta.

        Best-effort: si el proveedor no responde, degrada a score 0.0 para no
        romper la cadena de evaluacion.
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(f"{self._base_url}/check",
                                   json={"source_code": source_code})
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            log.warning("Proveedor externo de plagio no disponible: %s", exc)
            return ExternalCheck(score=0.0, matches=[])

        # Traduccion: el proveedor habla 'similarity_score' y 'matches[].url'.
        score = float(data.get("similarity_score", 0.0))
        matches = [
            PlagiarismMatch(
                source="turnitin",
                similarity=float(m.get("similarity", score)),
                reference=m.get("url"),
            )
            for m in data.get("matches", [])
        ]
        return ExternalCheck(score=score, matches=matches)
