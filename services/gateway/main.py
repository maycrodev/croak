"""gateway — punto de entrada unico de CROAK (CLAUDE.md seccion 4).

Responsabilidades:
  - Exponer una sola API publica (puerto 8000).
  - Validar el JWT y propagar la identidad ya verificada a los servicios internos
    via cabeceras `X-User-Id` / `X-User-Role`.
  - Enrutar cada request al microservicio destino segun el primer segmento de ruta.
"""
from __future__ import annotations

import os

import httpx
import jwt
from fastapi import FastAPI, HTTPException, Request, Response

from libs.common.config import settings
from libs.common.jwt_utils import decode_token
from libs.common.logging_config import configure_logging

SERVICE_NAME = "gateway"
log = configure_logging(SERVICE_NAME, settings.log_level)

# Prefijo de ruta -> URL base del servicio destino (puertos fijos, CLAUDE.md 4).
ROUTES: dict[str, str] = {
    "auth": os.environ.get("IDENTITY_URL", "http://identity-service:8001"),
    "users": os.environ.get("IDENTITY_URL", "http://identity-service:8001"),
    "assignments": os.environ.get("ASSIGNMENT_URL", "http://assignment-service:8002"),
    "submissions": os.environ.get("SUBMISSION_URL", "http://submission-service:8003"),
    "executions": os.environ.get("EXECUTION_URL", "http://execution-service:8004"),
    "grades": os.environ.get("GRADING_URL", "http://grading-service:8005"),
    "plagiarism": os.environ.get("PLAGIARISM_URL", "http://plagiarism-service:8006"),
    "lms": os.environ.get("LMS_URL", "http://lms-integration-service:8007"),
    "audit": os.environ.get("AUDIT_URL", "http://audit-service:8008"),
}

# Rutas accesibles sin token: (metodo, ruta-exacta).
PUBLIC_ROUTES: set[tuple[str, str]] = {
    ("POST", "auth/login"),
    ("POST", "users"),
}

app = FastAPI(title=SERVICE_NAME)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/")
def root():
    return {
        "service": SERVICE_NAME,
        "status": "ok",
        "message": "API Gateway de CROAK. Autenticarse en POST /auth/login.",
        "routes": sorted(ROUTES.keys()),
    }


def _authenticate(request: Request) -> dict:
    """Valida el Bearer token y devuelve los claims; lanza 401 si es invalido."""
    authorization = request.headers.get("authorization")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Falta el token Bearer")
    try:
        return decode_token(authorization.split(" ", 1)[1])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token invalido o expirado")


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(full_path: str, request: Request):
    """Catch-all: valida (si aplica) y reenvia la request al servicio destino."""
    segment = full_path.split("/")[0]
    base_url = ROUTES.get(segment)
    if base_url is None:
        raise HTTPException(status_code=404, detail=f"Sin ruta configurada para /{full_path}")

    forward_headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }
    if (request.method, full_path) not in PUBLIC_ROUTES:
        claims = _authenticate(request)
        forward_headers["X-User-Id"] = str(claims.get("sub", ""))
        forward_headers["X-User-Role"] = str(claims.get("role", ""))

    body = await request.body()
    target_url = f"{base_url}/{full_path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            upstream = await client.request(
                request.method,
                target_url,
                content=body,
                headers=forward_headers,
                params=request.url.query,
            )
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail=f"Servicio '{segment}' no disponible")

    log.info("%s /%s -> %s [%s]", request.method, full_path, segment, upstream.status_code)
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )
