# ADR-006 — Fuente de stdout para los criterios `metrics`

**Estado:** aceptado (MVP3) · **Inciso:** VII

## Contexto

Un criterio `metrics` evalúa propiedades del stdout del programa (reglas
`regex` / `contains`). A diferencia de un `test_case`, una regla `metrics` **no
aporta un `stdin`**, así que hay que decidir contra qué salida se evalúa.

## Decisión

Las reglas `metrics` se evalúan contra el stdout de una **corrida baseline con
`stdin` vacío**. El `execution-service` ejecuta esa corrida **siempre**, adicional
a las corridas por cada test_case, y la persiste en `ExecutionResult.baseline_run`.

## Alternativa considerada

Evaluar las métricas contra el stdout de la primera corrida por test_case. Se
descartó: ataría las métricas a que exista al menos un test_case y mezclaría dos
conceptos distintos —una métrica describe una propiedad del **programa**, no de
un caso concreto—.

## Consecuencias

- Una corrida extra (~10 ms) por submission, aunque la assignment no use métricas.
- El estado agregado del `ExecutionResult` refleja los **test_cases**, no la
  baseline: un programa que lee `stdin` falla en la baseline (EOF), y eso es
  esperado — no debe degradar el estado de la ejecución.
- El grading combina ambas partes: `final_score = min(100, test_cases + metrics)`.
