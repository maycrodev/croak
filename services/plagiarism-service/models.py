"""Modelo ORM del plagiarism-service."""
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, func

from db import Base


class PlagiarismReportRow(Base):
    """Reporte de plagio de una submission: similitud interna + externa."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, nullable=False, index=True)
    internal_score = Column(Float, nullable=False, default=0.0)
    external_score = Column(Float, nullable=False, default=0.0)
    flagged = Column(Boolean, nullable=False, default=False)
    threshold = Column(Float, nullable=False, default=0.7)
    matches = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
