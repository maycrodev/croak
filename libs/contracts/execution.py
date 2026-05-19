"""Contrato del resultado de ejecucion en sandbox (execution-service, inciso I)."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

ExecutionStatus = Literal["success", "runtime_error", "timeout", "error"]


class CaseRun(BaseModel):
    """Resultado de ejecutar el codigo del estudiante contra un caso de prueba.

    El sandbox corre una vez por cada caso de prueba de la assignment (un caso
    aporta su `stdin`); si la assignment no tiene casos, se hace una sola corrida.
    """

    case_index: int
    stdin: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    duration_ms: int = 0
    timed_out: bool = False
    status: ExecutionStatus = "success"


class ExecutionResult(BaseModel):
    """Resultado agregado de ejecutar una submission en el sandbox."""

    id: Optional[int] = None
    submission_id: int
    status: ExecutionStatus = "success"
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    duration_ms: int = 0
    timed_out: bool = False
    runs: list[CaseRun] = []
    # Corrida con stdin vacio; su stdout alimenta los criterios 'metrics' (ADR-006).
    baseline_run: Optional[CaseRun] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
