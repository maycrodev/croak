"""turnitin-mock — proveedor externo de plagio simulado (CLAUDE.md seccion 6).

Expone POST /check y devuelve un `similarity_score` DETERMINISTA derivado del
hash del contenido, para que las demos sean reproducibles. El plagiarism-service
lo consume a traves de un Adapter, de modo que cambiar a un TurnItIn real solo
toque ese adaptador.
"""
import hashlib

from fastapi import FastAPI
from pydantic import BaseModel

SERVICE_NAME = "turnitin-mock"

app = FastAPI(title=SERVICE_NAME)


class CheckRequest(BaseModel):
    source_code: str = ""


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.post("/check")
def check(payload: CheckRequest):
    """Devuelve un puntaje de similitud externo determinista (0.00 - 0.59)."""
    digest = hashlib.sha256(payload.source_code.encode("utf-8")).hexdigest()
    score = (int(digest[:8], 16) % 6000) / 10000.0
    matches = []
    if score > 0.30:
        matches.append({
            "url": f"https://repositorio.ejemplo.edu/doc/{digest[:10]}",
            "similarity": round(score, 4),
        })
    return {"similarity_score": round(score, 4), "matches": matches}
