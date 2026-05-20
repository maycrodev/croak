# ADR-007 — Formato del export anual de auditoría

**Estado:** aceptado (MVP4) · **Contexto:** b) auditoría estatal anual

## Contexto

Las notas son auditadas anualmente por entidades estatales. Necesitan un export
de la bitácora del año que sea **inmutable y verificable** de forma independiente.

## Decisión

`GET /audit/export/annual?year=YYYY` devuelve un documento JSON con tres partes:
`metadata`, `events` (todos los eventos del año UTC) y `export_seal`.

- **JSON** como formato: legible, universal, sin dependencias para la entidad estatal.
- **`export_seal`** = SHA-256 del JSON canónico del documento **excluyendo el
  propio sello** (`json.dumps` con `sort_keys=True`, separadores compactos,
  `ensure_ascii=False`). La entidad recalcula el sello para detectar cualquier
  alteración del archivo exportado.
- **`metadata.integrity`**: verificación de la cadena de hashes restringida a los
  eventos del año (mismo algoritmo que `/audit/events/verify`, pero sin exigir el
  hash genesis, porque un año intermedio no arranca en el evento genesis).

## Consecuencias

- Doble garantía de inmutabilidad: la hash-chain interna de los eventos **más**
  el `export_seal` externo del documento completo.
- Un año sin eventos produce un documento válido vacío (`event_count=0`,
  `events=[]`, hashes en `null`), nunca un error.
