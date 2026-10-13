# Microservicio de Depósitos en Dólares (USD Deposit Microservice)
> **Curso:** Desarrollo de Aplicaciones para la Nube - Práctica 3  
> **Arquitectura:** Microservicios Cloud-Native, Spec-Driven Development, Agentic Workflow.

---

## 📁 Estructura del Proyecto

### 1. Especificaciones de Ingeniería (`specs/`)
Las especificaciones formales que rigen cada aspecto del microservicio:
- [01_business_domain_and_rules.md](file:///c:/Users/juan9/OneDrive/Desktop/CICLO%208/DESARROLLO%20DE%20APLICACIONES%20PARA%20LA%20NUBE/PRACTICA%203/specs/01_business_domain_and_rules.md): Ciclo de vida del depósito, matriz de estados, validaciones AML/PLD, límites diarios y reglas monetarias USD.
- [02_api_contracts_rfc7807.md](file:///c:/Users/juan9/OneDrive/Desktop/CICLO%208/DESARROLLO%20DE%20APLICACIONES%20PARA%20LA%20NUBE/PRACTICA%203/specs/02_api_contracts_rfc7807.md): Contratos OpenAPI/REST, headers requeridos (`X-Idempotency-Key`, `X-Correlation-ID`), catálogo de errores RFC 7807 y contrato externo con el Microservicio de Cuentas.
- [03_data_architecture_and_db_schema.md](file:///c:/Users/juan9/OneDrive/Desktop/CICLO%208/DESARROLLO%20DE%20APLICACIONES%20PARA%20LA%20NUBE/PRACTICA%203/specs/03_data_architecture_and_db_schema.md): Esquema DDL en PostgreSQL con precisión `NUMERIC(15,2)`, tablas de idempotencia, log inmutable de auditoría y Outbox pattern.
- [04_cloud_resilience_and_integration.md](file:///c:/Users/juan9/OneDrive/Desktop/CICLO%208/DESARROLLO%20DE%20APLICACIONES%20PARA%20LA%20NUBE/PRACTICA%203/specs/04_cloud_resilience_and_integration.md): Circuit Breaker, reintentos con exponential backoff + jitter, health checks (`/health/live`, `/health/ready`) y 12-Factor config.
- [05_observability_and_security.md](file:///c:/Users/juan9/OneDrive/Desktop/CICLO%208/DESARROLLO%20DE%20APLICACIONES%20PARA%20LA%20NUBE/PRACTICA%203/specs/05_observability_and_security.md): Logging estructurado en JSON, métricas Prometheus (`/metrics`) y enmascaramiento de datos bancarios (PII).

### 2. Agentes de Desarrollo (`agentes/`)
Roles especializados para ejecutar la construcción por fases:
- [01_architect_agent.md](file:///c:/Users/juan9/OneDrive/Desktop/CICLO%208/DESARROLLO%20DE%20APLICACIONES%20PARA%20LA%20NUBE/PRACTICA%203/agentes/01_architect_agent.md): Validador de arquitectura hexagonal y cumplimiento normativo.
- [02_backend_fastapi_agent.md](file:///c:/Users/juan9/OneDrive/Desktop/CICLO%208/DESARROLLO%20DE%20APLICACIONES%20PARA%20LA%20NUBE/PRACTICA%203/agentes/02_backend_fastapi_agent.md): Desarrollador de endpoints, modelos Pydantic, SQLAlchemy asíncrono y llamadas con `httpx`.
- [03_qa_testing_agent.md](file:///c:/Users/juan9/OneDrive/Desktop/CICLO%208/DESARROLLO%20DE%20APLICACIONES%20PARA%20LA%20NUBE/PRACTICA%203/agentes/03_qa_testing_agent.md): Diseñador de pruebas unitarias, de integración, idempotencia y mocks con `pytest` y `respx`.
- [04_devops_cloud_agent.md](file:///c:/Users/juan9/OneDrive/Desktop/CICLO%208/DESARROLLO%20DE%20APLICACIONES%20PARA%20LA%20NUBE/PRACTICA%203/agentes/04_devops_cloud_agent.md): Creador del Dockerfile, Docker Compose con PostgreSQL y servidor mock de Cuentas.
