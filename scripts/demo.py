"""demo.py - Ejecuta AUTOMATICAMENTE el flujo completo de CROAK (escenarios A-E).

Equivalente a scripts/demo.http pero sin clics: corre todo de un tiron, narra los
resultados y verifica las aserciones clave. Sirve a la vez de demo y de smoke test.
Solo usa la libreria estandar de Python (urllib) - no requiere instalar nada.

Uso:
    python scripts/demo.py

Requisitos: `docker compose up` corriendo + `python scripts/seed.py` ya ejecutado.
Variable opcional: CROAK_GATEWAY_URL (por defecto http://localhost:8000).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

GATEWAY = os.environ.get("CROAK_GATEWAY_URL", "http://localhost:8000")

_passed = 0
_failed = 0

# Codigo de ejemplo: lee dos enteros de stdin e imprime su suma.
SUMA_OK = "a, b = map(int, input().split())\nprint(a + b)\n"
SUMA_MALA = "print(0)\n"
# Codigo del escenario D: imprime un marcador + la suma de lo que reciba.
MIXTO = ('import sys\n'
         'nums = sys.stdin.read().split()\n'
         'print("RESULT")\n'
         'print(sum(int(n) for n in nums))\n')


def _request(method, path, payload=None, token=None):
    """HTTP request al gateway. Devuelve (status_code, body)."""
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{GATEWAY}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"null")
    except urllib.error.URLError as exc:
        print(f"\nNo se pudo conectar al gateway ({exc}). Esta corriendo docker compose up?")
        sys.exit(1)


def _section(title):
    print(f"\n{'=' * 66}\n {title}\n{'=' * 66}")


def _check(label, condition):
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"   [OK]    {label}")
    else:
        _failed += 1
        print(f"   [FALLO] {label}")


def _login(email, password):
    status, body = _request("POST", "/auth/login", {"email": email, "password": password})
    if status != 200:
        print(f"ERROR: login de {email} fallo (HTTP {status}). "
              f"Ejecutaste 'python scripts/seed.py'?")
        sys.exit(1)
    return body["access_token"], body["user"]["id"]


def _assignment(professor_id, title, deadline, criteria):
    return {"professor_id": professor_id, "title": title, "description": title,
            "language": "python", "deadline": deadline, "attempt_policy": "best",
            "criteria": criteria}


_CASES_SUMA = [{"kind": "test_cases", "name": "Casos basicos", "test_cases": [
    {"stdin": "2 3\n", "expected_stdout": "5", "points": 50},
    {"stdin": "10 20\n", "expected_stdout": "30", "points": 50},
]}]


def health_checks():
    _section("0. Health checks")
    _, body = _request("GET", "/health")
    _check(f"gateway responde ({body})", body and body.get("status") == "ok")


def scenario_a(prof_token, prof_id, st_token, st_id, st2_token, st2_id):
    _section("ESCENARIO A - Entrega dentro de plazo (incisos I, II, III, IV)")
    _, asg = _request("POST", "/assignments",
                      _assignment(prof_id, "Suma de dos enteros",
                                  "2026-12-31T23:59:00Z", _CASES_SUMA), prof_token)
    aid = asg["id"]
    print(f"   assignment creada id={aid}")

    _, sub = _request("POST", "/submissions",
                      {"assignment_id": aid, "student_id": st_id,
                       "language": "python", "source_code": SUMA_OK}, st_token)
    sid = sub["id"]
    _check(f"submission {sid} quedo en status=graded", sub.get("status") == "graded")

    _, ex = _request("GET", f"/executions/{sid}", token=st_token)
    _check("ejecucion en sandbox status=success", ex.get("status") == "success")

    _, gr = _request("GET", f"/grades/{sid}", token=st_token)
    _check(f"nota = {gr.get('score')}/100 (esperado 100)", gr.get("score") == 100.0)

    _, lms = _request("GET", f"/lms/sync/{sid}", token=prof_token)
    _check(f"sincronizacion LMS status={lms.get('status')}", lms.get("status") == "synced")

    # Segundo estudiante copia el codigo -> plagio interno detectado.
    _, sub2 = _request("POST", "/submissions",
                       {"assignment_id": aid, "student_id": st2_id,
                        "language": "python", "source_code": SUMA_OK}, st2_token)
    _, plag = _request("GET", f"/plagiarism/{sub2['id']}", token=st2_token)
    _check(f"plagio del codigo copiado flagged={plag.get('flagged')} "
           f"(interno={plag.get('internal_score')})", plag.get("flagged") is True)


def scenario_b(prof_token, prof_id, st_token, st_id):
    _section("ESCENARIO B - Entrega fuera de plazo (inciso V)")
    _, asg = _request("POST", "/assignments",
                      _assignment(prof_id, "Tarea vencida", "2020-01-01T00:00:00Z",
                                  _CASES_SUMA), prof_token)
    status, body = _request("POST", "/submissions",
                            {"assignment_id": asg["id"], "student_id": st_id,
                             "language": "python", "source_code": SUMA_OK}, st_token)
    _check(f"entrega tardia rechazada con HTTP {status} (esperado 422)", status == 422)
    _check("error = submission_after_deadline",
           body.get("error") == "submission_after_deadline")
    rid = body.get("submission_id")
    _, rej = _request("GET", f"/submissions/{rid}", token=prof_token)
    _check(f"submission {rid} persistida con status={rej.get('status')}",
           rej.get("status") == "rejected")


def scenario_c(prof_token, prof_id, st_token, st_id):
    _section("ESCENARIO C - Intentos ilimitados, politica best (inciso VI)")
    _, asg = _request("POST", "/assignments",
                      _assignment(prof_id, "Suma - varios intentos",
                                  "2026-12-31T23:59:00Z", _CASES_SUMA), prof_token)
    aid = asg["id"]
    _, s1 = _request("POST", "/submissions",
                     {"assignment_id": aid, "student_id": st_id,
                      "language": "python", "source_code": SUMA_MALA}, st_token)
    _, g1 = _request("GET", f"/grades/{s1['id']}", token=st_token)
    print(f"   intento 1 (incorrecto): nota {g1.get('score')}")
    _, s2 = _request("POST", "/submissions",
                     {"assignment_id": aid, "student_id": st_id,
                      "language": "python", "source_code": SUMA_OK}, st_token)
    _, g2 = _request("GET", f"/grades/{s2['id']}", token=st_token)
    print(f"   intento 2 (correcto):   nota {g2.get('score')}")
    _, eff = _request("GET", f"/grades/effective?assignment_id={aid}&student_id={st_id}",
                      token=prof_token)
    _check(f"nota efectiva = {eff.get('effective_score')} (esperado 100, la mejor)",
           eff.get("effective_score") == 100.0)
    _check(f"intento de origen = #{eff.get('source_submission_id')} (el 2do)",
           eff.get("source_submission_id") == s2["id"])


def scenario_d(prof_token, prof_id, st_token, st_id):
    _section("ESCENARIO D - Criterio mixto: test_cases + metrics (inciso VII)")
    criteria = [
        {"kind": "test_cases", "name": "Suma correcta", "test_cases": [
            {"stdin": "4 6\n", "expected_stdout": "RESULT\n10", "points": 60}]},
        {"kind": "metrics", "name": "Formato de salida", "rules": [
            {"type": "contains", "pattern": "RESULT", "points": 30},
            {"type": "regex", "pattern": "[0-9]+", "points": 30}]},
    ]
    _, asg = _request("POST", "/assignments",
                      _assignment(prof_id, "Tarea con criterio mixto",
                                  "2026-12-31T23:59:00Z", criteria), prof_token)
    _, sub = _request("POST", "/submissions",
                      {"assignment_id": asg["id"], "student_id": st_id,
                       "language": "python", "source_code": MIXTO}, st_token)
    _, gr = _request("GET", f"/grades/{sub['id']}", token=st_token)
    bd = gr.get("breakdown", {})
    print(f"   breakdown: {bd}")
    _check("test_cases aporta 60 puntos", bd.get("test_cases_score") == 60.0)
    _check("metrics aporta 60 puntos", bd.get("metrics_score") == 60.0)
    _check(f"nota final con tope 100 (raw 120) = {gr.get('score')}",
           gr.get("score") == 100.0 and bd.get("capped_at_100") is True)


def scenario_e(admin_token, st_token):
    _section("ESCENARIO E - Auditoria estatal (contexto b)")
    _, verify = _request("GET", "/audit/events/verify", token=admin_token)
    _check(f"cadena de hashes intacta ({verify.get('total_events')} eventos)",
           verify.get("intact") is True)

    _, doc = _request("GET", "/audit/export/annual?year=2026", token=admin_token)
    seal = doc.pop("export_seal", None)
    canonical = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    recomputed = hashlib.sha256(canonical.encode()).hexdigest()
    _check("export anual 2026: export_seal recalculado coincide", seal == recomputed)

    _, empty = _request("GET", "/audit/export/annual?year=1999", token=admin_token)
    _check("export de un anio sin eventos = documento vacio valido",
           empty.get("metadata", {}).get("event_count") == 0)

    status, _ = _request("GET", "/audit/events/verify", token=st_token)
    _check(f"un estudiante NO puede verificar (HTTP {status}, esperado 403)",
           status == 403)


def main():
    print(f"CROAK - demo automatica end-to-end\nGateway: {GATEWAY}")
    health_checks()

    prof_token, prof_id = _login("prof@croak.edu", "prof123")
    st_token, st_id = _login("estudiante@croak.edu", "estu123")
    st2_token, st2_id = _login("estudiante2@croak.edu", "estu123")
    admin_token, _ = _login("admin@croak.edu", "admin123")

    scenario_a(prof_token, prof_id, st_token, st_id, st2_token, st2_id)
    scenario_b(prof_token, prof_id, st_token, st_id)
    scenario_c(prof_token, prof_id, st_token, st_id)
    scenario_d(prof_token, prof_id, st_token, st_id)
    scenario_e(admin_token, st_token)

    _section(f"RESULTADO: {_passed} OK, {_failed} fallidos")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
