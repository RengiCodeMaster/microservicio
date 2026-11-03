# SPEC-08 — Configuración, despliegue y operación

Versión: 2.1. Objetivos iniciales propuestos, verificables en entorno de referencia.

## 1. Procesos y health (OPS-001)

Procesos separados API y worker, misma versión y DB. Local Docker Compose: PostgreSQL, mock durable, API y worker; issuer JWT de prueba con claves ficticias y fixtures sólo locales. Un comando documentado levanta entorno; migración es paso explícito y único antes de API/worker, no competencia entre réplicas.

GET /health/live: 200 {"status":"UP"} si proceso atiende; no consulta dependencias.
GET /health/ready: deadline 1 s; SELECT 1 y versión de esquema compatible. 200 {"status":"READY","database":"UP","schema":"COMPATIBLE","accounts":"AVAILABLE"}; accounts puede ser DEGRADED con 200 si breaker abierto. DB/schema incompatible o apagado: 503 {"status":"NOT_READY","database":"DOWN","schema":"UNKNOWN","accounts":"UNKNOWN"} con valores reales cuando se conocen. No publicar DSN ni endpoints.
Worker publica heartbeat en tabla/runtime interno cada 10 s; alerta si ningún worker actualizado en 60 s y hay jobs pendientes.

Imagen reproducible, dependencias fijadas, usuario sin privilegios, puerto 8000, sin secretos incrustados, filesystem de aplicación de sólo lectura salvo temporales. No escoger proveedor cloud obligatorio: demo local es entregable; infraestructura real se define después con DEC-06.

## 2. Configuración obligatoria

ENV development/testing/production; DATABASE_URL y ACCOUNTS_SERVICE_URL requeridas; PORT default 8000. Dinero en variables como cadenas decimales, no float.

| Variable | Default / validación |
| --- | --- |
| POLICY_VERSION | usd-v1; no vacío. |
| MIN_DEPOSIT_USD | 1.00; >0. |
| MAX_BRANCH_DEPOSIT_USD | 50000.00; >=mínimo. |
| MAX_ATM_DEPOSIT_USD / MAX_PARTNER_DEPOSIT_USD | 5000.00; >=mínimo. |
| DAILY_LIMIT_USD | 20000.00; >=mínimo. |
| AML_THRESHOLD_USD | 10000.00; >0. |
| HTTP_REQUEST_DEADLINE_SEC | 8; >0. |
| ACCOUNT_LOOKUP_DEADLINE_SEC / CREDIT_DEADLINE_SEC | 2 / 3; menores al presupuesto HTTP. |
| HTTP_CONNECT_TIMEOUT_SEC / HTTP_POOL_TIMEOUT_SEC | 0.5 / 0.2. |
| LOOKUP_READ_TIMEOUT_SEC / CREDIT_READ_TIMEOUT_SEC | 1.5 / 2.5. |
| HTTP_WRITE_TIMEOUT_SEC | 0.5. |
| CIRCUIT_FAILURE_THRESHOLD / CIRCUIT_OPEN_SEC | 5 / 30. |
| WORKER_CONCURRENCY / API_EXTERNAL_CONCURRENCY | 10 / 20. |
| JOB_LEASE_SEC / JOB_HEARTBEAT_SEC | 30 / 10; lease >=3×heartbeat. |
| RECONCILIATION_MAX_CYCLES / MAX_AGE_SEC | 20 / 86400. |
| PENDING_JOB_ADMISSION_LIMIT | 10000; >0. |
| JWT_ISSUER / JWT_JWKS_URL / JWT_AUDIENCE | Requeridas; audience usd-deposits. |
| ACCOUNTS_SERVICE_TOKEN_SECRET | Referencia secreta requerida fuera de mock. |
| LOG_LEVEL | INFO; enum DEBUG/INFO/WARNING/ERROR. |
| DB_LOCK_TIMEOUT_MS / DB_STATEMENT_TIMEOUT_MS | 500 / 2000. |
| DB_POOL_SIZE_API / DB_POOL_SIZE_WORKER | 10 / 5 por proceso, max_overflow=0. |

Config inválida impide arranque. Production prohíbe issuer de prueba, auth deshabilitada, SQLite y endpoints de inyección de fallos. Los valores que alteran reglas requieren cambio de versión de política; no se modifica snapshot de depósitos anteriores. Cuotas de rate limit y retención según SPEC-05 se documentan en configuración de gateway/tareas, no como overrides ocultos.

## 3. Objetivos medibles (OPS-002)

Entorno de referencia: API 2 vCPU/512 MiB, worker 2 vCPU/512 MiB, PostgreSQL 2 vCPU/2 GiB, red local y mock con latencia p95 <=200 ms; registrar versiones y hardware real para comparación.
Carga: 20 solicitudes/s durante 10 min, 20% crear, 70% consultar, 10% historial, hasta 50 solicitudes en vuelo, dataset 100000 depósitos.
Objetivos: consultas p95 <=300 ms; creación saludable p95 <=2 s; aceptación durable responde dentro de 8 s; cero abonos duplicados y cero sobreasignación del cupo.
Degradación: Cuentas indisponible 5 min; consultas conservan objetivo, nuevas admisiones devuelven 202 mientras hay capacidad, trabajo sin pérdida, recuperación de cola <=15 min tras restaurar dependencia bajo carga anterior.

SLO propuesto: disponibilidad mensual 99.5% de API para peticiones válidas (200/201/202/errores de negocio cuentan como respuesta válida; 5xx de plataforma no). Es objetivo, no garantía demostrada por pruebas locales. Capacidad/infraestructura se ajustan según medición; no relajar invariantes para cumplir latencia.

## 4. Backups y recuperación (OPS-003)

Objetivo inicial RPO <=5 min y RTO <=60 min con PostgreSQL + archivo WAL/PITR; backup base diario, cifrado y retención 30 días. Ejecutar restauración de prueba mensual y registrar duración/consistencia.

RPO no permite perder evidencia contable silenciosamente: tras restauración mantener nuevas admisiones deshabilitadas, recuperar referencias desde ledger autoritativo de Cuentas y evidencia del canal para intervalo perdido, importar/conciliar bajo operación controlada y deduplicar antes de habilitar. Si Cuentas no puede exportar créditos por source_system e intervalo, recuperación productiva queda bloqueada (DEC-08). No generar IDs distintos para créditos perdidos.

Runbook DB caída: detener admisión, preservar jobs, recuperar conexión y reclamar leases.
Runbook Cuentas caída: revisar breaker/credenciales, conservar pendientes/cupo, reanudar lookup.
Runbook MANUAL_REVIEW: obtener evidencia externa por referencia, corregir dependencia y solicitar conciliación; nunca editar estado directo.
Runbook reserva vieja: verificar crédito; no liberar por fecha.
Runbook despliegue: backup/verificación esquema, migración única, rolling deploy API/worker, smoke de lectura y salud, rollback de aplicación sólo si esquema compatible.

## 5. Puerta de entrega (OPS-004)

Requiere OpenAPI validado, migraciones probadas, configuración de ejemplo sin secretos, Compose documentado, aceptación SPEC-07, prueba de recuperación y reporte de riesgos externos. CI ejecuta lint/tipos y suites relevantes; sólo PostgreSQL demuestra concurrencia. Escaneo de dependencias e imagen al publicar. No ejecutar scripts de migración destructivos automáticamente.

README debe describir fuente normativa, pasos reproducibles, identidad de prueba, cómo ejecutar API/worker/migraciones/tests y cómo verificar demo. En esta fase sólo se publica ruta de lectura SDD; comandos no verificados no se presentan como existentes.
