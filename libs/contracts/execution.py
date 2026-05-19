"""Contrato del resultado de ejecucion en sandbox (execution-service, inciso I)."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

ExecutionStatus = Literal["success", "runtime_error", "timeout", "error"]


class ExecutionResult(BaseModel):
    """Salida capturada de ejecutar el codigo del estudiante en el sandbox."""

    id: Optional[int] = None
    submission_id: int
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    duration_ms: int = 0
    timed_out: bool = False
    status: ExecutionStatus = "success"
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
