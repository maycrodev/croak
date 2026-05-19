"""Contratos Pydantic compartidos entre servicios (contract-first, CLAUDE.md 7).

Los servicios consumen estos esquemas, NO la implementacion de sus pares.
Cada agente puede ANADIR archivos aqui; no reescribir masivamente los existentes.
"""
from .assignment import (
    AssignmentCreate,
    AssignmentPublic,
    GradingCriterion,
    MetricRule,
    TestCase,
)
from .audit import AuditEvent, AuditEventIn
from .execution import CaseRun, ExecutionResult
from .grade import EffectiveGrade, Grade
from .lms import LmsSyncRecord, LmsSyncRequest
from .plagiarism import PlagiarismMatch, PlagiarismReport
from .submission import SubmissionCreate, SubmissionDetail, SubmissionPublic
from .user import LoginRequest, Role, TokenResponse, UserCreate, UserPublic

__all__ = [
    "AssignmentCreate",
    "AssignmentPublic",
    "GradingCriterion",
    "MetricRule",
    "TestCase",
    "AuditEvent",
    "AuditEventIn",
    "CaseRun",
    "ExecutionResult",
    "EffectiveGrade",
    "Grade",
    "LmsSyncRecord",
    "LmsSyncRequest",
    "PlagiarismMatch",
    "PlagiarismReport",
    "SubmissionCreate",
    "SubmissionDetail",
    "SubmissionPublic",
    "LoginRequest",
    "Role",
    "TokenResponse",
    "UserCreate",
    "UserPublic",
]
