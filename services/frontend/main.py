"""frontend — Panel de Auditoria de CROAK (servicio aislado, solo lectura).

Servicio independiente en el puerto 5173. Consume las APIs del gateway con un JWT
admin (obtenido server-side) y renderiza un dashboard con Jinja2. No expone auth
propia ni JavaScript. Si este servicio se cae, NO afecta a ningun otro: es 100%
aditivo respecto a la plataforma.
"""
from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

SERVICE_NAME = "frontend"
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://gateway:8000")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@croak.edu")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

logging.basicConfig(
    level=logging.INFO, stream=sys.stdout,
    format='{"level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)
log = logging.getLogger(SERVICE_NAME)

# JWT admin guardado en memoria del proceso.
_state: dict[str, str | None] = {"token": None}


def _login() -> str | None:
    """Autentica como admin contra el gateway. Devuelve el JWT o None si falla."""
    try:
        resp = httpx.post(
            f"{GATEWAY_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10.0,
        )
        resp.raise_for_status()
        log.info("login admin OK contra %s", GATEWAY_URL)
        return resp.json()["access_token"]
    except (httpx.HTTPError, KeyError) as exc:
        log.warning("login admin fallo: %s", exc)
        return None


def _api_get(path: str):
    """GET autenticado al gateway. Devuelve el JSON, o None si algo falla.

    Reintenta una vez si el token expiro (HTTP 401).
    """
    if not _state["token"]:
        _state["token"] = _login()
    if not _state["token"]:
        return None
    url = f"{GATEWAY_URL}{path}"
    try:
        resp = httpx.get(
            url, headers={"Authorization": f"Bearer {_state['token']}"}, timeout=10.0
        )
        if resp.status_code == 401:  # token expirado: re-login y un reintento
            _state["token"] = _login()
            if not _state["token"]:
                return None
            resp = httpx.get(
                url, headers={"Authorization": f"Bearer {_state['token']}"}, timeout=10.0
            )
        return resp.json() if resp.status_code == 200 else None
    except httpx.HTTPError as exc:
        log.warning("GET %s fallo: %s", path, exc)
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    _state["token"] = _login()
    log.info("frontend iniciado (gateway=%s)", GATEWAY_URL)
    yield


app = FastAPI(title=SERVICE_NAME, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Mapea un estado a una clase de badge CSS.
_BADGE = {
    "synced": "ok", "graded": "ok", "success": "ok", "executed": "ok", "ok": "ok",
    "failed": "bad", "error": "bad", "runtime_error": "bad",
    "rejected": "warn", "timeout": "warn",
    "received": "neutral", "executing": "neutral",
}


def _badge(value) -> str:
    return _BADGE.get(str(value).lower(), "neutral")


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    """Renderiza el panel: widget de integridad + tabla de submissions."""
    verify = _api_get("/audit/events/verify")
    users = _api_get("/users") or []
    assignments = _api_get("/assignments") or []
    submissions = _api_get("/submissions") or []

    user_map = {u["id"]: u["full_name"] for u in users}
    asg_map = {a["id"]: a["title"] for a in assignments}

    rows = []
    for sub in submissions:
        sid = sub["id"]
        grade = _api_get(f"/grades/{sid}")
        plagiarism = _api_get(f"/plagiarism/{sid}")
        lms = _api_get(f"/lms/sync/{sid}")
        rows.append({
            "id": sid,
            "student": user_map.get(sub["student_id"], f"#{sub['student_id']}"),
            "assignment": asg_map.get(sub["assignment_id"], f"#{sub['assignment_id']}"),
            "attempt": sub["attempt_number"],
            "status": sub["status"],
            "status_badge": _badge(sub["status"]),
            "score": f"{grade['score']:.0f} / {grade['max_score']:.0f}" if grade else "—",
            "plagiarism": f"{plagiarism['internal_score']:.2f}" if plagiarism else "—",
            "lms": lms["status"] if lms else "—",
            "lms_badge": _badge(lms["status"]) if lms else "neutral",
        })

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "auth_ok": _state["token"] is not None,
        "verify": verify,
        "rows": rows,
    })
