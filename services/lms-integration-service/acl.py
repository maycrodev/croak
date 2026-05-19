"""Anti-Corruption Layer (ACL) entre CROAK y el mainframe LMS legacy.

================================ PIEZA CLAVE ================================
ESTE archivo es el UNICO lugar de toda la plataforma que conoce el formato feo
del mainframe: el registro de ancho fijo y los codigos numericos de respuesta.
El resto del lms-integration-service trabaja solo con el modelo limpio
(GradeEvent / SyncResult). Migrar a un LMS distinto = reescribir solo este
archivo. Layout completo: docs/arquitectura/adr-005-mainframe-layout.md.
=============================================================================

Contiene exactamente dos funciones de traduccion:
  - to_mainframe(GradeEvent) -> bytes      (modelo limpio  -> registro feo)
  - from_mainframe(dict)     -> SyncResult (respuesta fea  -> modelo limpio)
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

# --- Layout del registro de ancho fijo (80 caracteres) ---
RECORD_LENGTH = 80
_STUDENT_ID_WIDTH = 12      # posiciones  0-11
_ASSIGNMENT_ID_WIDTH = 12   # posiciones 12-23
_GRADE_WIDTH = 6            # posiciones 24-29  -> formato NNN.NN
_TIMESTAMP_WIDTH = 14       # posiciones 30-43  -> YYYYMMDDHHMMSS
_RESERVED_WIDTH = 36        # posiciones 44-79  -> espacios

# --- Tabla de traduccion de codigos del mainframe al estado interno limpio ---
_RESPONSE_CODES = {
    "0000": ("synced", "Sincronizacion aceptada por el mainframe"),
    "0012": ("failed", "El mainframe rechazo el registro (error de validacion)"),
    "0099": ("failed", "Error interno del mainframe"),
}
_UNKNOWN_CODE = ("failed", "Codigo de respuesta desconocido del mainframe")


@dataclass
class GradeEvent:
    """Modelo LIMPIO interno: una nota lista para sincronizar con el LMS."""

    student_id: int
    assignment_id: int
    grade: float  # 0-100


@dataclass
class SyncResult:
    """Resultado LIMPIO de una sincronizacion (sin rastro del formato mainframe)."""

    status: str   # 'synced' | 'failed'
    code: str
    message: str


def to_mainframe(event: GradeEvent) -> bytes:
    """Traduce el modelo limpio al registro COBOL de ancho fijo de 80 caracteres.

    STUDENT_ID e ASSIGNMENT_ID se alinean a la izquierda con relleno de espacios;
    GRADE se formatea como NNN.NN con ceros a la izquierda; TIMESTAMP es UTC.
    """
    student = str(event.student_id)[:_STUDENT_ID_WIDTH].ljust(_STUDENT_ID_WIDTH)
    assignment = str(event.assignment_id)[:_ASSIGNMENT_ID_WIDTH].ljust(_ASSIGNMENT_ID_WIDTH)
    clamped = max(0.0, min(100.0, event.grade))
    grade = f"{clamped:0{_GRADE_WIDTH}.2f}"  # p.ej. 95.5 -> '095.50'
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    reserved = " " * _RESERVED_WIDTH

    record = f"{student}{assignment}{grade}{timestamp}{reserved}"
    if len(record) != RECORD_LENGTH:  # invariante del layout
        raise ValueError(f"Registro de {len(record)} chars, se esperaban {RECORD_LENGTH}")
    return record.encode("ascii")


def from_mainframe(response: dict) -> SyncResult:
    """Traduce la respuesta del mainframe (codigo numerico) al modelo limpio."""
    code = str(response.get("code", "0099"))
    status, default_message = _RESPONSE_CODES.get(code, _UNKNOWN_CODE)
    message = response.get("message") or default_message
    return SyncResult(status=status, code=code, message=message)
