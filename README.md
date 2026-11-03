# Microservicio de depósitos en dólares — especificación SDD

El proyecto define un servicio que registra, valida y coordina depósitos USD con un microservicio de Cuentas. Cuentas realiza el abono; Depósitos conserva trazabilidad, idempotencia, reservas de límite y conciliación.

La base documental es **versión 2.1, propuesta implementable del 2026-10-13**. El código existente no se ha adaptado ni validado contra esta revisión. Los límites y requisitos AML son políticas académicas propuestas. El registro de correcciones está en SPEC-09, sección 6.

## Ruta de lectura

| Spec | Qué resuelve |
| --- | --- |
| [00 — Alcance y gobierno SDD](specs/00_scope_and_sdd_governance.md) | Objetivo, exclusiones, vocabulario y proceso de cambios. |
| [01 — Dominio](specs/01_business_domain_and_rules.md) | Reglas monetarias, actores, estados e idempotencia. |
| [02 — API y Cuentas](specs/02_api_contracts_rfc7807.md) | Campos, validaciones, respuestas, errores y contrato externo. |
| [03 — Datos](specs/03_data_architecture_and_db_schema.md) | Esquema lógico, constraints, transacciones, reservas y concurrencia. |
| [04 — Resiliencia](specs/04_cloud_resilience_and_integration.md) | Timeouts, jobs, reintentos y conciliación. |
| [05 — Seguridad y observabilidad](specs/05_observability_and_security.md) | Autorización por recurso, privacidad, auditoría y métricas. |
| [06 — Arquitectura](specs/06_architecture_and_implementation_blueprint.md) | Capas, puertos y secuencia de construcción. |
| [07 — Aceptación](specs/07_acceptance_and_traceability.md) | 52 escenarios trazables y evidencia requerida. |
| [08 — Operación](specs/08_operations_and_delivery.md) | Configuración, despliegue, carga, backup y recuperación. |
| [09 — Decisiones y riesgos](specs/09_decisions_and_integration_risks.md) | Motivos, cambios y dependencias externas pendientes. |

Leer en ese orden antes de implementar. Markdown es la fuente normativa actual; OpenAPI 3.1 y migraciones son entregables de las siguientes fases. La ruta histórica de SPEC-02 conserva rfc7807 en su nombre; el contrato usa RFC 9457.

## Roles de trabajo

Las instrucciones de [Arquitectura](agentes/01_architect_agent.md), [Backend](agentes/02_backend_fastapi_agent.md), [QA](agentes/03_qa_testing_agent.md) y [DevOps](agentes/04_devops_cloud_agent.md) guían implementación futura. No sustituyen las specs ni autorizan ignorar contradicciones.

## Cómo continuar

1. Revisar decisiones propuestas y dependencias externas en SPEC-09.
2. Derivar y validar OpenAPI y migraciones.
3. Implementar por casos de uso siguiendo SPEC-06.
4. Ejecutar SPEC-07 y entregar evidencia junto al runbook de SPEC-08.

Demo local usa PostgreSQL y mock contractual. Integración real exige acuerdo con Cuentas para idempotencia durable, consulta por referencia y recuperación del ledger. Un timeout nunca equivale a una reversión financiera.
