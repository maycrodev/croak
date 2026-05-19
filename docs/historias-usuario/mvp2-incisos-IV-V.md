# Historias de Usuario — MVP2 (incisos IV, V)

Trazables a las reglas del dominio (CLAUDE.md §1) y al plan de MVPs (§2).

---

## Inciso IV — Integración con el LMS de la universidad

### HU-IV.1 — Sincronizar la nota con el LMS

**Como** universidad
**quiero** que la nota calculada se envíe automáticamente al LMS institucional
**para** que el estudiante la vea en el sistema oficial sin recarga manual.

**Criterios de aceptación:**
- Al registrarse una nota, el `grading-service` la envía al `lms-integration-service`.
- La nota se traduce al formato del mainframe y se hace `POST /COBOL/GRADESYNC`.
- El resultado queda persistido en `lms_sync.lms_sync` y consultable por
  `GET /lms/sync/{submission_id}`.

### HU-IV.2 — Aislar el LMS legacy con un Anti-Corruption Layer

**Como** equipo de la plataforma
**quiero** que el formato tosco del mainframe quede encapsulado en un solo lugar
**para** poder cambiar de LMS sin reescribir el resto del sistema.

**Criterios de aceptación:**
- Toda la traducción modelo-limpio ↔ formato-mainframe vive en `acl.py`.
- El resto del servicio sólo conoce el modelo limpio (`GradeEvent`, `SyncResult`).
- Los códigos numéricos del mainframe se traducen a estados limpios (`synced`/`failed`).

### HU-IV.3 — Tolerancia a fallos del mainframe

**Como** universidad
**quiero** que un fallo de sincronización no invalide la nota local
**para** no perder calificaciones por la inestabilidad del mainframe.

**Criterios de aceptación:**
- La sincronización es best-effort: un fallo se registra pero no revierte la nota.
- Tanto el intento como el resultado dejan evento de auditoría.

---

## Inciso V — Fecha límite de entrega

### HU-V.1 — Definir una fecha límite

**Como** profesor
**quiero** definir una fecha y hora límite para cada tarea
**para** que no se acepten entregas fuera de plazo.

**Criterios de aceptación:**
- La `Assignment` persiste una `deadline`.

### HU-V.2 — Rechazar entregas tardías

**Como** profesor
**quiero** que las entregas posteriores al deadline se rechacen con un error claro
**para** garantizar la equidad entre estudiantes.

**Criterios de aceptación:**
- Si `now > deadline`, `POST /submissions` responde **HTTP 422** con el error y
  la fecha límite.
- La entrega tardía se persiste con `status=rejected` y
  `rejection_reason=after_deadline` (queda en auditoría — inciso II).
- Una entrega rechazada **no** dispara ejecución, calificación ni plagio.
- Dentro de plazo, el flujo es el normal de MVP1.
