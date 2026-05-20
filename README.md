# CROAK — Plataforma de Evaluación Automática de Código

> Plataforma de **microservicios** que recibe el código de los estudiantes, lo
> ejecuta en un **sandbox**, lo califica, detecta **plagio** (interno + externo),
> sincroniza las notas con el **LMS mainframe** de la universidad mediante un
> **Anti-Corruption Layer**, y mantiene una **bitácora de auditoría inmutable**
> encadenada por hash. Python + FastAPI + PostgreSQL + Docker Compose.
>
> Frog Software Ltda. — Hackathon 3. Cobertura de rúbrica: **100% (MVP1–MVP4)**.

---

## 1. Cómo levantar

```bash
# Construir y levantar toda la plataforma (12 contenedores)
docker compose up -d --build

# Sembrar los usuarios de demo (admin, profesor, 2 estudiantes)
python scripts/seed.py
```

Comprobar que todo está arriba:

```bash
docker compose ps
curl http://localhost:8000/health        # gateway
```

La demo completa de la API está en [`scripts/demo.http`](scripts/demo.http)
(extensión **REST Client** de VS Code). `python scripts/seed.py` solo usa la
librería estándar — no requiere instalar nada.

> La constitución del proyecto (`CLAUDE.md`) vive **fuera** de este repositorio,
> en la carpeta superior, por decisión de diseño.

---

## 2. Mapa de servicios

| Servicio | Puerto | Schema | Responsabilidad |
|----------|--------|--------|-----------------|
| `gateway` | 8000 | — | Punto de entrada único; valida JWT; enruta; propaga identidad |
| `identity-service` | 8001 | `identity` | Usuarios, roles, login, emisión de JWT |
| `assignment-service` | 8002 | `assignment` | Tareas: deadline y criterios de calificación |
| `submission-service` | 8003 | `submission` | Carga de código, intentos, orquestación de la cadena |
| `execution-service` | 8004 | `execution` | Ejecución del código en sandbox (subproceso + rlimits) |
| `grading-service` | 8005 | `grading` | Calificación (`test_cases` + `metrics`) y nota efectiva |
| `plagiarism-service` | 8006 | `plagiarism` | Similitud interna (k-gram/winnowing) + adaptador externo |
| `lms-integration-service` | 8007 | `lms_sync` | Anti-Corruption Layer hacia el mainframe LMS |
| `audit-service` | 8008 | `audit` | Bitácora append-only, hash-chain, export anual |
| `turnitin-mock` | 8011 | — | Servicio externo de plagio simulado (determinista) |
| `lms-mainframe-mock` | 8012 | — | Mainframe LMS legacy simulado (registro de ancho fijo) |
| PostgreSQL | 5432 | (todos) | Persistencia relacional — un schema por servicio |

Una sola instancia de PostgreSQL, **un schema por servicio** (database-per-service
lógico). Sin claves foráneas entre schemas: las relaciones cruzadas se resuelven
por ID + llamada HTTP.

---

## 3. Demo end-to-end (`scripts/demo.http`)

Cinco escenarios encadenables en una sola corrida:

| Escenario | Qué demuestra |
|-----------|---------------|
| **A** | Entrega dentro de plazo: código → sandbox → nota 100/100 → sync con el LMS → reporte de plagio. |
| **B** | Entrega fuera de plazo: `POST /submissions` a una tarea vencida → **HTTP 422**, submission `rejected` (queda auditada). |
| **C** | Intentos ilimitados (política `best`): 2 intentos del mismo estudiante → `GET /grades/effective` devuelve la mejor nota. |
| **D** | Criterio mixto: `test_cases` + `metrics` (regex/contains) → `final_score = min(100, suma)` con desglose. |
| **E** | Auditoría estatal: `GET /audit/events/verify` (integridad de la cadena) + `GET /audit/export/annual?year=2026` (export sellado). |

---

## Panel de Auditoría (frontend)

Una vez levantados los servicios, abre **http://localhost:5173/** en el navegador para ver el panel:
- Widget de integridad de la bitácora (verde si la cadena está íntegra, rojo si fue alterada).
- Tabla de submissions con nota, score de plagio interno y estado de sincronización con el LMS.

El frontend es un servicio aislado (puerto 5173) que consume las APIs del gateway. Si se cae, no afecta a los demás servicios ni a la demo por `scripts/demo.http`.

---

## 4. Trazabilidad de la rúbrica

### MVP1 — 60% · incisos I, II, III
- **I** — sube → ejecuta → califica: `submission-service` orquesta `execution-service`
  (sandbox) → `grading-service` (nota persistente).
- **II** — persistente y auditable: `audit-service`, bitácora append-only encadenada
  por hash; cada paso emite un evento.
- **III** — plagio: `plagiarism-service` (k-gram + winnowing → Jaccard interno) +
  `turnitin-mock` vía patrón Adapter.

### MVP2 — 70% · incisos IV, V
- **IV** — integración LMS: `lms-integration-service` con **Anti-Corruption Layer**
  (`acl.py`) ↔ `lms-mainframe-mock` (`POST /COBOL/GRADESYNC`).
- **V** — deadline: `submission-service` rechaza con **HTTP 422** las entregas
  posteriores a la fecha límite (`status=rejected`).

### MVP3 — 80% · incisos VI, VII
- **VI** — intentos ilimitados: historial completo de submissions;
  `grading-service` → `GET /grades/effective` aplica la política `best`/`last`.
- **VII** — criterios del profesor: `assignment-service` admite criterios
  `test_cases` y `metrics`; `grading-service` los evalúa y combina.

### MVP4 — 100% · contexto b)
- **Auditoría estatal anual**: `audit-service` → `GET /audit/events/verify`
  (verificación de integridad) y `GET /audit/export/annual?year=YYYY`
  (export inmutable con `export_seal` SHA-256).

---

## 5. Guion de presentación — Demo en vivo (5 puntos visuales clave)

1. **Auditoría tamper-evident** — alterar el `payload` de un evento directamente en
   Postgres → `GET /audit/events/verify` lo detecta (`intact:false`, `first_break_id`)
   → restaurar → `intact:true`. *Es lo más fuerte: va primero.*
2. **Anti-Corruption Layer al mainframe** — abrir
   [`services/lms-integration-service/acl.py`](services/lms-integration-service/acl.py)
   y mostrar `to_mainframe` / `from_mainframe`; mostrar el `raw_request` de 80
   caracteres en `lms_sync.lms_sync`.
3. **Sandbox con timeout duro** — una submission con `time.sleep(30)` se corta a
   los 10 s → nota 0/100, `status=timeout`.
4. **Plagio doble** — una submission idéntica de otro estudiante → Jaccard 1.0
   interno + score del `turnitin-mock` → `flagged:true`.
5. **Export anual con sello forense** — `GET /audit/export/annual?year=2026` →
   recalcular el `export_seal` por separado → **MATCH**.

---

## 6. Documentación

- **Arquitectura y decisiones (ADRs):**
  [`docs/arquitectura/README.md`](docs/arquitectura/README.md) — diagrama de
  microservicios y ADR-1 a ADR-5 (microservicios, PostgreSQL, ACL, sandbox,
  hash-chain). Detalle por MVP:
  [ADR-005 layout del mainframe](docs/arquitectura/adr-005-mainframe-layout.md) ·
  [ADR-006 fuente de stdout para métricas](docs/arquitectura/adr-006-metrics-stdout-source.md) ·
  [ADR-007 formato del export anual](docs/arquitectura/adr-007-annual-export-format.md).
- **Historias de usuario:**
  [`docs/historias-usuario/`](docs/historias-usuario/README.md) — HU por inciso/MVP.
- **Carátula del entregable:** [`docs/caratula.md`](docs/caratula.md).

---

## 7. Estructura del repositorio

```
croak/
  docker-compose.yml      # toda la plataforma (12 contenedores)
  libs/contracts/         # esquemas Pydantic compartidos (contract-first)
  libs/common/            # config, DB, JWT, logging, cliente de auditoría
  services/               # un microservicio por carpeta
  mocks/                  # sistemas externos simulados (turnitin, mainframe)
  scripts/                # seed.py + demo.http
  docs/                   # carátula, arquitectura (ADRs), historias de usuario
```

---
