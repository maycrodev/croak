# gateway

Punto de entrada unico de CROAK. Puerto **8000**, sin base de datos.

- Valida el JWT HS256 emitido por `identity-service`.
- Propaga la identidad verificada a los servicios internos con las cabeceras
  `X-User-Id` y `X-User-Role`.
- Enruta por el primer segmento de la ruta:

| Prefijo | Servicio destino |
|---------|------------------|
| `/auth/*`, `/users/*` | identity-service :8001 |
| `/assignments/*` | assignment-service :8002 |
| `/submissions/*` | submission-service :8003 |
| `/executions/*` | execution-service :8004 |
| `/grades/*` | grading-service :8005 |
| `/plagiarism/*` | plagiarism-service :8006 |
| `/lms/*` | lms-integration-service :8007 |
| `/audit/*` | audit-service :8008 |

Rutas publicas (sin token): `POST /auth/login` y `POST /users`.
