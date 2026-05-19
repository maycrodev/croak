# Historias de Usuario — MVP3 (incisos VI, VII)

Trazables a las reglas del dominio (CLAUDE.md §1) y al plan de MVPs (§2).

---

## Inciso VI — Intentos ilimitados

### HU-VI.1 — Reenviar para mejorar la nota

**Como** estudiante
**quiero** poder enviar mi solución cuantas veces quiera antes del deadline
**para** mejorar mi calificación.

**Criterios de aceptación:**
- Cada reenvío crea una submission nueva con `attempt_number` incremental.
- Se conserva el historial completo: ningún intento sobrescribe a otro.
- Cada intento genera su propia ejecución y su propia nota.

### HU-VI.2 — Nota efectiva según la política del profesor

**Como** profesor
**quiero** definir si cuenta la mejor nota o la última de los intentos
**para** aplicar mi criterio pedagógico.

**Criterios de aceptación:**
- `assignment.attempt_policy` admite `best` (mejor nota) o `last` (último intento).
- `GET /grades/effective?assignment_id=&student_id=` devuelve la nota efectiva,
  el intento de origen y la política aplicada.
- En `best`, ante empate gana el intento más reciente.
- La nota que se sincroniza con el LMS es la **efectiva**, no la del último intento.

---

## Inciso VII — Criterios de calificación definidos por el profesor

### HU-VII.1 — Calificar por métricas sobre la salida

**Como** profesor
**quiero** definir criterios que busquen patrones en la salida del programa
**para** evaluar aspectos que no son una comparación exacta de stdout.

**Criterios de aceptación:**
- Un criterio `metrics` admite reglas `regex` y `contains`, cada una con sus puntos.
- Las reglas se evalúan sobre el stdout de una corrida con `stdin` vacío (ADR-006).

### HU-VII.2 — Combinar pruebas y métricas

**Como** profesor
**quiero** combinar casos de prueba y métricas en una misma tarea
**para** componer la calificación como yo decida.

**Criterios de aceptación:**
- Una `Assignment` puede llevar criterios `test_cases` y `metrics` a la vez.
- `final_score = min(100, puntos_test_cases + puntos_metrics)`.
- El `Grade` persiste un `breakdown` con `test_cases_score`, `metrics_score` y
  `capped_at_100`.
