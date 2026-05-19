# ADR-005 — Layout del registro del mainframe LMS

**Estado:** aceptado (MVP2) · **Incisos:** IV

## Contexto

El LMS de la universidad corre sobre un **mainframe legacy** difícil de modificar.
Su API es deliberadamente tosca: recibe un **registro de ancho fijo** estilo COBOL
y responde con **códigos numéricos**. El `lms-integration-service` implementa un
**Anti-Corruption Layer** (`acl.py`) para que esa fealdad no contamine el resto
de la plataforma.

## Decisión — Layout del registro `GRADESYNC` (80 caracteres)

`POST /COBOL/GRADESYNC` recibe en el body un registro ASCII de exactamente **80
caracteres**:

| Campo | Posiciones | Long. | Formato | Relleno |
|-------|-----------|-------|---------|---------|
| `STUDENT_ID` | 0–11 | 12 | numérico, alineado a la izquierda | espacios a la derecha |
| `ASSIGNMENT_ID` | 12–23 | 12 | numérico, alineado a la izquierda | espacios a la derecha |
| `GRADE` | 24–29 | 6 | `NNN.NN` (punto físico) | ceros a la izquierda |
| `TIMESTAMP` | 30–43 | 14 | `YYYYMMDDHHMMSS` (UTC) | — |
| `RESERVED` | 44–79 | 36 | espacios | — |

**Total: 12 + 12 + 6 + 14 + 36 = 80.**

Ejemplo (`STUDENT_ID=3`, `ASSIGNMENT_ID=1`, `GRADE=95.5`):

```
3           1           095.5020260519232800
```
(`STUDENT_ID`/`ASSIGNMENT_ID` rellenados con espacios; `RESERVED` = 36 espacios)

### Nota sobre el campo `GRADE` (corrección de inconsistencia del enunciado)

El enunciado pedía `GRADE` de **5** caracteres con formato `NNN.NN` y ejemplo
`095.50`. `NNN.NN` con **punto físico** ocupa **6** caracteres, no 5
(`12+12+5+14+37 = 81`, no cuadra con 80). Se respetan los elementos **explícitos
y con ejemplo** del enunciado —formato `NNN.NN`, "el punto cuenta como char",
ejemplo `095.50`— y se ajusta `RESERVED` de 37 a **36** para que el registro
sume exactamente 80. Cualquier consumidor debe usar las posiciones de la tabla.

## Códigos de respuesta

El mainframe responde con JSON `{"code": "NNNN", "message": "..."}`:

| Código | Significado | Estado interno (`acl.from_mainframe`) |
|--------|-------------|----------------------------------------|
| `0000` | OK — sincronización aceptada | `synced` |
| `0012` | Error de validación (formato/longitud/rango) | `failed` |
| `0099` | Error interno del mainframe | `failed` |

## Consecuencias

- **Toda** la dependencia del formato del mainframe vive en
  `services/lms-integration-service/acl.py` (funciones `to_mainframe` /
  `from_mainframe`). Migrar a otro LMS = reescribir solo ese archivo.
- `lms_sync.lms_sync` guarda `raw_request` y `raw_response` exactos: la
  traducción del ACL queda auditable.
- MVP2 hace **un solo intento** de sincronización (sin reintentos automáticos);
  un fallo queda registrado y visible vía `GET /lms/sync/{submission_id}`.
