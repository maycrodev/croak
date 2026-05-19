"""Modelo ORM del lms-integration-service."""
from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from db import Base


class LmsSyncRow(Base):
    """Estado de la sincronizacion de la nota de una submission con el mainframe.

    `raw_request` / `raw_response` guardan exactamente lo enviado/recibido del
    mainframe: dejan auditable la traduccion del ACL.
    """

    __tablename__ = "lms_sync"

    submission_id = Column(Integer, primary_key=True)
    student_id = Column(Integer, nullable=False)
    assignment_id = Column(Integer, nullable=False)
    grade = Column(Float, nullable=False)
    mainframe_response_code = Column(String(4), nullable=False)
    status = Column(String(10), nullable=False)  # synced | failed
    synced_at = Column(DateTime(timezone=True), nullable=False)
    raw_request = Column(Text, nullable=False, default="")
    raw_response = Column(Text, nullable=False, default="")
