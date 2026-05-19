# CROAK — Plataforma de Evaluación Automática de Código

> Frog Software Ltda. — Hackathon 3. Sistema de microservicios que recibe código
> de estudiantes, lo ejecuta en un sandbox, lo califica, detecta plagio, sincroniza
> con el LMS de la universidad y mantiene una bitácora de auditoría inmutable.
>
> La constitución del proyecto está en `CLAUDE.md` (fuera de este repositorio, en
> la carpeta superior). Léela antes de contribuir.

## Stack

Python 3.11 · FastAPI · PostgreSQL 16 · SQLAlchemy 2 · Docker Compose · JWT HS256.

## Cómo levantar

```bash
# 1) (opcional) copiar variables de entorno
cp .env.example .env

# 2) construir y levantar toda la plataforma
docker compose up --build

# 3) en otra terminal, sembrar datos de demo (admin, profesor, estudiante)
python scripts/seed.py
```

Comprobar que todo está arriba:

```bash
docker compose ps
curl http://localhost:8000/health      # gateway
curl http://localhost:8001/health      # identity-service
```

La demo de la API está en `scripts/demo.http` (extensión REST Client de VS Code).

## Mapa de servicios

| Servicio | Puerto | Schema | Estado | Responsabilidad |
|----------|--------|--------|--------|------------------|
| `gateway` | 8000 | — | **Implementado** | Entrada única, valida JWT, enruta |
| `identity-service` | 8001 | `identity` | **Implementado** | Usuarios, roles, login, JWT |
| `assignment-service` | 8002 | `assignment` | Placeholder | Tareas: deadline y criterios |
| `submission-service` | 8003 | `submission` | Placeholder | Carga de código, intentos |
| `execution-service` | 8004 | `execution` | Placeholder | Ejecución en sandbox |
| `grading-service` | 8005 | `grading` | Placeholder | Calificación persistente |
| `plagiarism-service` | 8006 | `plagiarism` | Placeholder | Similitud + adaptador externo |
| `lms-integration-service` | 8007 | `lms_sync` | Placeholder | Anti-Corruption Layer al LMS |
| `audit-service` | 8008 | `audit` | Placeholder | Bitácora append-only, hash-chain |
| `turnitin-mock` | 8011 | — | Placeholder | Servicio externo de plagio simulado |
| `lms-mainframe-mock` | 8012 | — | Placeholder | Mainframe LMS simulado |
| PostgreSQL | 5432 | (todos) | Implementado | Persistencia relacional |

Los servicios *placeholder* ya arrancan y exponen `GET /health`; su lógica se
construye en los MVP1–MVP4 (ver `CLAUDE.md` sección 2).

## Estructura

```
croak/
  docker-compose.yml      # toda la plataforma
  libs/contracts/         # esquemas Pydantic compartidos (contract-first)
  libs/common/            # config, DB, JWT, logging, cliente de auditoría
  services/               # un microservicio por carpeta
  mocks/                  # sistemas externos simulados
  scripts/                # seed.py + demo.http
  docs/                   # carátula, arquitectura (ADRs), historias de usuario
```

## Enlaces GitHub

<!-- El orquestador humano pega aquí las URLs del repositorio. -->

- Repositorio: _(pendiente)_
- Tablero / issues: _(pendiente)_

## Documentación

- Arquitectura y decisiones (ADRs): [`docs/arquitectura/`](docs/arquitectura/README.md)
- Historias de usuario: [`docs/historias-usuario/`](docs/historias-usuario/README.md)
- Carátula del entregable: [`docs/caratula.md`](docs/caratula.md)
