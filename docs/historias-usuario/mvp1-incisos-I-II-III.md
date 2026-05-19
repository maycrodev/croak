# Historias de Usuario — MVP1 (incisos I, II, III)

Trazables a las reglas del dominio (CLAUDE.md §1) y al plan de MVPs (§2).

---

## Inciso I — Subir, ejecutar y calificar código

### HU-I.1 — Enviar código para evaluación

**Como** estudiante
**quiero** subir el código fuente de mi solución a una tarea
**para** que el sistema lo ejecute y lo califique automáticamente.

**Criterios de aceptación:**
- `POST /submissions` con `assignment_id`, `student_id`, `language` y `source_code`
  crea el envío y responde `201`.
- El envío dispara la cadena ejecución → calificación → plagio.
- Cada envío queda registrado con su número de intento.

### HU-I.2 — Ejecutar el código en un entorno seguro

**Como** plataforma
**quiero** ejecutar el código no confiable del estudiante en un sandbox aislado
**para** obtener su salida sin poner en riesgo el sistema.

**Criterios de aceptación:**
- El código se ejecuta con límite de CPU, de memoria y timeout duro (10 s).
- Se captura `stdout`, `stderr`, código de salida y tiempo de ejecución.
- Un programa que excede el tiempo se marca como `timeout` sin colgar el servicio.

### HU-I.3 — Calificar según los criterios del profesor

**Como** profesor
**quiero** definir casos de prueba (entrada → salida esperada → puntos)
**para** que la nota del estudiante se calcule de forma objetiva y reproducible.

**Criterios de aceptación:**
- La nota es la suma de los puntos de los casos cuya salida coincide con la esperada.
- La nota se persiste con el desglose por caso (`detail`).
- `GET /grades/{submission_id}` devuelve la nota y su desglose.

---

## Inciso II — Persistencia y auditabilidad

### HU-II.1 — Registro de auditoría inmutable

**Como** entidad auditora (estatal)
**quiero** que cada ejecución y calificación quede en una bitácora inalterable
**para** poder verificar la integridad de las notas a posteriori.

**Criterios de aceptación:**
- Cada paso (envío, ejecución, calificación, plagio) genera un evento de auditoría.
- Cada evento encadena el `hash` del evento anterior (`prev_hash`).
- La bitácora es append-only: no expone modificación ni borrado.

### HU-II.2 — Consultar la traza de un envío

**Como** profesor o auditor
**quiero** consultar todos los eventos asociados a un envío
**para** entender qué le ocurrió y cuándo.

**Criterios de aceptación:**
- `GET /audit/events?entity_type=&entity_id=&service=` filtra la bitácora.
- Los eventos se devuelven en orden cronológico.
- Los datos persisten en PostgreSQL (`audit.events`).

---

## Inciso III — Detección de plagio

### HU-III.1 — Similitud contra otros envíos

**Como** profesor
**quiero** que el sistema compare cada envío con los demás de la misma tarea
**para** detectar copias entre estudiantes.

**Criterios de aceptación:**
- Se calcula similitud con fingerprinting k-gram + winnowing → índice de Jaccard.
- Se reporta el puntaje interno máximo y con qué envío coincide.

### HU-III.2 — Verificación contra servicio externo

**Como** profesor
**quiero** que el envío también se contraste con un servicio externo (tipo TurnItIn)
**para** detectar copias de fuentes fuera de la plataforma.

**Criterios de aceptación:**
- El envío se consulta contra el servicio externo mediante un Adapter.
- El reporte combina puntaje interno y externo y marca `flagged` si supera el umbral.
- `GET /plagiarism/{submission_id}` devuelve el reporte completo.
