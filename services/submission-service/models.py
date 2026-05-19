"""Modelo ORM del submission-service."""
from sqlalchemy import Column, DateTime, Integer, String, Text, func

from db import Base


class Submission(Base):
    """Un envio de codigo de un estudiante para una assignment.

    Se conserva el historial completo: cada reenvio crea una fila nueva con
    `attempt_number` incremental (base para los intentos ilimitados del inciso VI).
    """

    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(Integer, nullable=False, index=True)
    student_id = Column(Integer, nullable=False, index=True)
    language = Column(String(50), nullable=False, default="python")
    source_code = Column(Text, nullable=False)
    attempt_number = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="received")
    failure_reason = Column(Text, nullable=True)
    rejection_reason = Column(String(40), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
