"""Modelo ORM del assignment-service."""
from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, func

from db import Base


class Assignment(Base):
    """Tarea de programacion definida por un profesor.

    `criteria` se guarda como JSON (lista de GradingCriterion); en MVP1 contiene
    casos de prueba. `deadline` se persiste pero su enforcement llega en MVP2.
    """

    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    professor_id = Column(Integer, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    language = Column(String(50), nullable=False, default="python")
    deadline = Column(DateTime(timezone=True), nullable=False)
    attempt_policy = Column(String(20), nullable=False, default="best")
    criteria = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
