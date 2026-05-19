"""lms-mainframe-mock — mainframe LMS legacy simulado (CLAUDE.md seccion 6).

Simula a proposito una API tosca: recibe un registro de ancho fijo de 80
caracteres estilo COBOL y responde con codigos numericos de 4 digitos. El
lms-integration-service implementa el Anti-Corruption Layer que aisla esta
fealdad del resto de la plataforma.

Layout del registro (ver docs/arquitectura/adr-005-mainframe-layout.md):
  STUDENT_ID[0:12]  ASSIGNMENT_ID[12:24]  GRADE[24:30]  TIMESTAMP[30:44]  RESERVED[44:80]
"""
import re

from fastapi import FastAPI, Request

SERVICE_NAME = "lms-mainframe-mock"
RECORD_LENGTH = 80

app = FastAPI(title=SERVICE_NAME)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


def _resp(code: str, message: str) -> dict:
    """Respuesta estilo mainframe: codigo numerico de 4 digitos + mensaje."""
    return {"code": code, "message": message}


@app.post("/COBOL/GRADESYNC")
async def gradesync(request: Request):
    """Recibe el registro de ancho fijo y devuelve un codigo numerico.

    0000 = OK | 0012 = error de validacion | 0099 = error interno.
    """
    try:
        raw = (await request.body()).decode("ascii", errors="replace")
    except Exception:  # noqa: BLE001 - el mainframe nunca lanza, solo codifica
        return _resp("0099", "INTERNAL ERROR")

    if len(raw) != RECORD_LENGTH:
        return _resp("0012", f"VALIDATION ERROR: RECORD LENGTH {len(raw)} EXPECTED 80")

    student_id = raw[0:12].strip()
    assignment_id = raw[12:24].strip()
    grade_field = raw[24:30]
    timestamp = raw[30:44]
    reserved = raw[44:80]

    if not student_id or not assignment_id:
        return _resp("0012", "VALIDATION ERROR: EMPTY STUDENT OR ASSIGNMENT ID")
    if not re.fullmatch(r"\d{3}\.\d{2}", grade_field):
        return _resp("0012", f"VALIDATION ERROR: BAD GRADE FORMAT [{grade_field}]")
    if not (0.0 <= float(grade_field) <= 100.0):
        return _resp("0012", f"VALIDATION ERROR: GRADE OUT OF RANGE [{grade_field}]")
    if not re.fullmatch(r"\d{14}", timestamp):
        return _resp("0012", f"VALIDATION ERROR: BAD TIMESTAMP [{timestamp}]")
    if len(reserved) != 36:  # RESERVED ocupa 36 chars (ver ADR-005)
        return _resp("0012", "VALIDATION ERROR: BAD RESERVED FIELD")

    # El mainframe acusa recibo; la persistencia real queda fuera del mock.
    return _resp(
        "0000",
        f"OK STUDENT {student_id} ASSIGNMENT {assignment_id} GRADE {grade_field}",
    )
