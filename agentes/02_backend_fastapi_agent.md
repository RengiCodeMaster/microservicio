# Agente 02 — Implementación backend según specs

## Objetivo

Implementar casos de uso de [SPEC-06](../specs/06_architecture_and_implementation_blueprint.md), conforme a toda la base [SDD](../specs/00_scope_and_sdd_governance.md). Si la tarea es sólo definición, no escribir código.

## Reglas

- Derivar primero OpenAPI 3.1 de [SPEC-02](../specs/02_api_contracts_rfc7807.md), no generar contrato desde comportamiento accidental del código.
- Dinero string en JSON, Decimal interno y NUMERIC(15,2) SQL.
- Dominio puro; aplicación depende de puertos; routers no hacen commits.
- PostgreSQL con migraciones, restricciones, auditoría y reservas según [SPEC-03](../specs/03_data_architecture_and_db_schema.md).
- Deducción de idempotencia por cuerpo completo/canal y ámbito; nunca consulta seguida de inserción sin constraint único.
- Replay inicial 201/202/error guardado; concurrente sin respuesta 409 IN_PROGRESS.
- Cuentas idempotente por deposit_reference y lookup autoritativo; nunca reintentar con nueva referencia.
- Continuación por worker durable; no BackgroundTasks como única garantía.
- Timeout conserva PENDING_RECONCILIATION y reserva; no FAILED_REVERSED.
- Autorización por cuenta/institución, incluidas listas, replay y comprobante.
- Relacionar cambios con IDs y escenarios; no presentar código como aceptado sin ejecutar pruebas.

## Entregable

Implementación, contratos y migraciones con evidencia de los AC correspondientes; dependencias externas declaradas. Toda desviación modifica specs/decisiones antes del código.

## Activación

“Implementa el caso de uso solicitado siguiendo SPEC-00..09, identifica requisitos y valida su aceptación; registra cualquier decisión faltante.”
