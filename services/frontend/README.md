# frontend — Panel de Auditoría (PLUS)

Servicio **aislado** de solo lectura. Puerto **5173**, sin base de datos.

Renderiza server-side (FastAPI + Jinja2, sin JavaScript) un dashboard que consume
las APIs del `gateway` con un JWT admin:

- **Widget de integridad** de la bitácora (`GET /audit/events/verify`).
- **Tabla de submissions**: id, estudiante, assignment, intento, status, nota
  final, score de plagio interno y estado de sincronización con el LMS.

Es 100% aditivo: no toca al `gateway` ni a ningún otro servicio. Si se cae, la
plataforma y `scripts/demo.http` siguen funcionando.

Variables de entorno: `GATEWAY_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.
