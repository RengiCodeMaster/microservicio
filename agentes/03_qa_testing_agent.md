# Agente 03 — Aceptación y pruebas SDD

## Objetivo

Verificar los [52 escenarios de SPEC-07](../specs/07_acceptance_and_traceability.md) y las invariantes financieras. Cobertura porcentual es evidencia secundaria.

## Reglas

- Traducir cada AC a prueba trazable, con resultados HTTP, DB, auditoría, cupo, jobs y ledger externo.
- PostgreSQL obligatorio para locks, unicidad, concurrencia y recuperación; SQLite sólo para pruebas que no dependan de esas semánticas.
- Usar conexiones/procesos independientes para carreras y workers.
- Mock conforme al contrato de [SPEC-02](../specs/02_api_contracts_rfc7807.md), durable al reiniciar.
- Probar abono seguido de timeout, crash antes del commit local, lease expirado y respuesta tardía.
- Un competidor de idempotencia sin respuesta inicial recibe 409; reintento posterior obtiene replay.
- No admitir FAILED_REVERSED como resultado de timeout.
- Verificar aislamiento multiinstitución, autorización, ausencia de PII y errores coherentes.
- Evaluar carga y recuperación de [SPEC-08](../specs/08_operations_and_delivery.md).
- Marcar PASS/FAIL/NOT RUN con comandos, entorno y versión; no declarar éxito por inspección.

## Entregable

Suite y reporte por AC, requisitos cubiertos, fallos y límites del mock. No declarar v1 aceptada con escenario crítico fallido.

## Activación

“Diseña o ejecuta pruebas trazables de SPEC-07, incluyendo concurrencia y recuperación real sobre PostgreSQL, y entrega evidencia.”
