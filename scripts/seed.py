"""seed.py - datos minimos para la demo de CROAK.

Crea un admin, un profesor y un estudiante llamando a la API a traves del gateway,
y hace un login de prueba. Es idempotente: si un usuario ya existe (HTTP 409) lo
informa y continua.

Uso:
    python scripts/seed.py

Requisitos: `docker compose up` corriendo. Solo usa la libreria estandar de
Python (urllib), no necesita instalar nada. Variable opcional CROAK_GATEWAY_URL.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

GATEWAY = os.environ.get("CROAK_GATEWAY_URL", "http://localhost:8000")

USERS = [
    {"email": "admin@croak.edu", "password": "admin123",
     "full_name": "Ada Admin", "role": "admin"},
    {"email": "prof@croak.edu", "password": "prof123",
     "full_name": "Pedro Profesor", "role": "professor"},
    {"email": "estudiante@croak.edu", "password": "estu123",
     "full_name": "Eva Estudiante", "role": "student"},
    {"email": "estudiante2@croak.edu", "password": "estu123",
     "full_name": "Bruno Estudiante", "role": "student"},
]


def _request(method: str, path: str, payload: dict | None = None, token: str | None = None):
    """Hace una request HTTP y devuelve (status_code, body_dict)."""
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{GATEWAY}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"null")


def seed_users() -> None:
    print("Creando usuarios de demo...")
    for user in USERS:
        status, body = _request("POST", "/users", user)
        if status == 201:
            print(f"  [creado]  {body['role']:<10} id={body['id']:<3} {body['email']}")
        elif status == 409:
            print(f"  [existe]  {user['role']:<10}       {user['email']}")
        else:
            print(f"  [ERROR]   {user['email']}: HTTP {status} {body}")
            sys.exit(1)


def smoke_login() -> None:
    print("\nLogin de prueba (profesor)...")
    status, body = _request("POST", "/auth/login",
                            {"email": "prof@croak.edu", "password": "prof123"})
    if status != 200:
        print(f"  [ERROR] login fallo: HTTP {status} {body}")
        sys.exit(1)
    token = body["access_token"]
    print(f"  Token JWT obtenido: {token[:48]}...")
    status, me = _request("GET", "/users/me", token=token)
    print(f"  GET /users/me -> HTTP {status}: {me}")


def main() -> int:
    print(f"Sembrando datos de demo via gateway: {GATEWAY}\n")
    try:
        seed_users()
        smoke_login()
    except urllib.error.URLError as exc:
        print(f"\nNo se pudo conectar al gateway ({exc}).", file=sys.stderr)
        print("Verifica que `docker compose up` este corriendo.", file=sys.stderr)
        return 1
    print("\nSeed completado. Datos listos para la demo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
