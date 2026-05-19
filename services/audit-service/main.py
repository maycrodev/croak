"""Servicio CROAK (placeholder de Stream A - Fundaciones).

Implementacion real pendiente segun el plan de MVPs (ver CLAUDE.md seccion 2).
Por ahora solo expone /health para que `docker compose up` levante el sistema
completo desde el primer momento.
"""
import os

from fastapi import FastAPI

SERVICE_NAME = os.environ.get("SERVICE_NAME", "unknown-service")

app = FastAPI(title=SERVICE_NAME)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/")
def root():
    return {
        "service": SERVICE_NAME,
        "status": "placeholder",
        "message": "Pendiente de implementacion (ver CLAUDE.md seccion 2).",
    }