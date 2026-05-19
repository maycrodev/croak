"""Modelo ORM del grading-service."""
from sqlalchemy import JSON, Column, DateTime, Float, Integer, func

from db import Base


class GradeRow(Base):
    """Nota persistente de una submission.

    `detail` (JSON) guarda el desglose por caso de prueba para que la nota sea
    auditable y explicable.
    """

    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, nullable=False, index=True)
    assignment_id = Column(Integer, nullable=False, index=True)
    student_id = Column(Integer, nullable=False, index=True)
    score = Column(Float, nullable=False, default=0.0)
    max_score = Column(Float, nullable=False, default=100.0)
    attempt_number = Column(Integer, nullable=False, default=1)
    detail = Column(JSON, nullable=False, default=dict)
    breakdown = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
