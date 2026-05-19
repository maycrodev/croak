"""Contratos Pydantic compartidos entre servicios (contract-first, CLAUDE.md 7).

Los servicios consumen estos esquemas, NO la implementacion de sus pares.
Cada agente puede ANADIR archivos aqui; no reescribir masivamente los existentes.
"""
from .assignment import AssignmentCreate, AssignmentPublic, GradingCriterion
from .audit import AuditEvent, AuditEventIn
from .execution import ExecutionResult
from .grade import Grade
from .plagiarism import PlagiarismMatch, PlagiarismReport
from .submission import SubmissionCreate, SubmissionPublic
from .user import LoginRequest, Role, TokenResponse, UserCreate, UserPublic

__all__ = [
    "AssignmentCreate",
    "AssignmentPublic",
    "GradingCriterion",
    "AuditEvent",
    "AuditEventIn",
    "ExecutionResult",
    "Grade",
    "PlagiarismMatch",
    "PlagiarismReport",
    "SubmissionCreate",
    "SubmissionPublic",
    "LoginRequest",
    "Role",
    "TokenResponse",
    "UserCreate",
    "UserPublic",
]
