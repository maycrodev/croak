"""Modelo ORM del identity-service."""
from sqlalchemy import Column, DateTime, Integer, String, func

from db import Base


class User(Base):
    """Usuario de la plataforma: estudiante, profesor o administrador."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="student")
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
