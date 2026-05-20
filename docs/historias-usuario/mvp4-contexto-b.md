# Historias de Usuario — MVP4 (contexto b)

Trazables al contexto b) del kata (CLAUDE.md §1) y al plan de MVPs (§2):
las notas son auditadas anualmente por entidades estatales.

---

## HU-b.1 — Verificar la integridad de la bitácora

**Como** auditor (administrador de la plataforma)
**quiero** verificar que la bitácora de auditoría no fue alterada
**para** poder confiar en que las ejecuciones y notas registradas son auténticas.

**Criterios de aceptación:**
- `GET /audit/events/verify` recalcula la cadena de hashes y devuelve `intact`,
  `total_events`, `genesis_ok`, `head_hash` y `first_break_id`.
- Si algún registro fue alterado, `intact=false` e indica el `first_break_id`.
- Sólo roles `admin` o `professor` pueden ejecutar la verificación.

## HU-b.2 — Export anual para la entidad estatal

**Como** entidad estatal auditora
**quiero** obtener todos los eventos de auditoría de un año en un documento sellado
**para** revisar la integridad de las notas de ese período de forma independiente.

**Criterios de aceptación:**
- `GET /audit/export/annual?year=YYYY` devuelve un documento JSON con `metadata`,
  `events` del año y un `export_seal` (SHA-256) recalculable de forma independiente.
- El documento incluye la verificación de integridad de los eventos del año.
- Un año sin eventos devuelve un documento válido vacío, no un error.
- Sólo el rol `admin` puede disparar el export.
