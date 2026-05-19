"""Modelo ORM del execution-service."""
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text, func

from db import Base


class ExecutionResultRow(Base):
    """Resultado de ejecutar una submission en el sandbox.

    `runs` (JSON) guarda el detalle por caso de prueba; los campos de primer nivel
    son el resumen agregado.
    """

    __tablename__ = "results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="success")
    stdout = Column(Text, nullable=False, default="")
    stderr = Column(Text, nullable=False, default="")
    exit_code = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=False, default=0)
    timed_out = Column(Boolean, nullable=False, default=False)
    runs = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
