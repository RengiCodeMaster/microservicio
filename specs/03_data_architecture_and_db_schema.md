# SPEC-03 — Persistencia y consistencia transaccional

Versión: 2.1. PostgreSQL 15+ es la base normativa. SQLite no demuestra bloqueos ni concurrencia de este contrato.

## 1. Modelo lógico (DAT-001)

UUID interno sin prefijo; la API convierte a dep_usd_<uuid>. Todas las fechas TIMESTAMPTZ UTC; dinero NUMERIC(15,2); booleanos no nullable. Identificadores externos no son FK a una base ajena. institution_id en todas las tablas de negocio; repositorios siempre filtran este ámbito.

| Tabla | Campos obligatorios y restricciones |
| --- | --- |
| usd_deposits | id UUID PK; institution_id VARCHAR(64); subject_id VARCHAR(128); target_account_id VARCHAR(64); amount NUMERIC(15,2) >0; currency='USD'; deposit_type enum SPEC-01; channel enum BRANCH/ATM/PARTNER/WEB/MOBILE; status enum de seis estados; origin_issuer VARCHAR(64); origin_reference VARCHAR(64); origin_details y policy_snapshot JSONB; policy_version VARCHAR(32); correlation_id UUID; version BIGINT >=1; created_at, updated_at. |
| Campos opcionales del depósito | aml_declaration JSONB; notes VARCHAR(500); account_service_tx_id VARCHAR(128); credited_at, completed_at, pii_anonymized_at; error_code VARCHAR(64). |
| account_limit_locks | institution_id, target_account_id como PK compuesta; fila durable que serializa reservas y terminalización por cuenta. |
| deposit_limit_reservations | deposit_id UUID PK/FK; institution_id, target_account_id; amount NUMERIC(15,2)>0; state ACTIVE/CONSUMED/RELEASED; reserved_at; resolved_at nullable sólo ACTIVE. |
| idempotency_records | institution_id, subject_id, operation CREATE/RECONCILE, idempotency_key UUID como PK compuesta; request_hash CHAR(64); deposit_id FK nullable hasta vincular; reconciliation_id UUID nullable; phase PROCESSING/RESPONDED/TOMBSTONE; response_code INT nullable; response_payload JSONB nullable; response_headers JSONB nullable; created_at; responded_at, response_expires_at nullable. |
| deposit_audit_log | id BIGINT identity PK; institution_id; deposit_id FK; previous_status nullable inicial; current_status; aggregate_version BIGINT; actor_id; action_code; correlation_id UUID; reason_code nullable; recorded_at. |
| processing_jobs | id UUID PK; institution_id; deposit_id FK; kind VALIDATE/CREDIT/RECONCILE; state READY/LEASED/DONE/MANUAL_REVIEW; phase nullable; generation BIGINT >=0; attempt_count INT >=0; reconciliation_cycle_count INT >=0; recovery_started_at nullable hasta recuperación; available_at; lease_owner, lease_until nullable; last_error_code nullable; created_at, updated_at. |
| reconciliation_requests | id UUID PK; institution_id; deposit_id FK; requested_by; reason VARCHAR(500) nullable sólo tras anonimización DAT-005; state QUEUED/RUNNING/DONE/MANUAL_REVIEW; processing_job_id FK; created_at; finished_at y reason_anonymized_at nullable. |
| external_attempts | id UUID PK; institution_id; deposit_id FK; job_id FK; sequence INT; operation LOOKUP_ACCOUNT/CREDIT/LOOKUP_CREDIT; started_at; finished_at nullable; outcome SUCCESS/DEFINITIVE_REJECTION/TRANSIENT/UNKNOWN/CONTRACT_ERROR nullable; http_status nullable; safe_error_code nullable. |

external_attempts nunca contiene bodies/token. origin_details y AML son datos sensibles con controles de SPEC-05. policy_snapshot incluye mínimo, máximo de canal, acumulado y umbral AML como strings.

Tipos abreviados de la tabla: institution_id VARCHAR(64), subject_id/actor_id/requested_by/lease_owner VARCHAR(128), target_account_id VARCHAR(64), códigos VARCHAR(64), timestamps TIMESTAMPTZ y estados VARCHAR(32) con CHECK de valores enumerados. phase es LOOKUP_ACCOUNT/SEND_CREDIT/LOOKUP_CREDIT o null. JSONB usa objetos, no arrays libres. FK de dependientes verifica institución con clave compuesta (institution_id,id) única en depósito; no aceptar hijo de otra institución. La evidencia se toma de la variante validada, no de campos libres nuevos.

CHECK de coherencia: phase RESPONDED en idempotencia exige response_code, response_payload, responded_at y response_expires_at; TOMBSTONE exige hash/vínculo, sin payload; PROCESSING no tiene respuesta. lease_owner/lease_until obligatorios sólo LEASED. Solicitudes DONE/MANUAL_REVIEW tienen finished_at; QUEUED/RUNNING no. Instantes updated_at/resolved_at no preceden created_at/reserved_at. Cada actualización de negocio del agregado incrementa version y guarda auditoría de transición cuando cambia estado; anonimización administrativa sigue DAT-005.

WEB/MOBILE se almacenan sólo para documentar rechazo durable ERR_CHANNEL_NOT_SUPPORTED; no pueden tener reserva ni intento de crédito ni estados PENDING_CREDIT/COMPLETED. En T1, origin_issuer/reference se derivan de la variante estructural del body, no del canal declarado. policy_snapshot usa máximo de canal NULL para WEB/MOBILE, cuya incompatibilidad se evalúa antes de reglas monetarias. Estos rechazos conservan la evidencia única igual que otros rechazos; no habilitan procesamiento financiero.

Unicidad: (institution_id, deposit_type, origin_issuer, origin_reference); (institution_id, account_service_tx_id) WHERE account_service_tx_id IS NOT NULL; auditoría (deposit_id, aggregate_version); un job no terminado por depósito usando índice parcial WHERE state IN ('READY','LEASED','MANUAL_REVIEW'); una solicitud manual activa por depósito WHERE state IN ('QUEUED','RUNNING'). MANUAL_REVIEW retiene el trabajo para no crear procesos paralelos; una solicitud manual reactiva ese mismo job.

En COMPLETED exigir tx_id, credited_at y completed_at no nulos; fuera de COMPLETED mantenerlos nulos. REJECTED exige error_code. Una reserva CONSUMED implica COMPLETED; RELEASED implica REJECTED. Las condiciones entre tablas se verifican mediante servicio transaccional y pruebas; CHECK simple no puede comprobar otra tabla.

## 2. Índices, migraciones y permisos (DAT-002)

Índices: depósitos (institution_id,target_account_id,completed_at DESC) filtrado COMPLETED; (institution_id,created_at DESC,id DESC) para historial; (institution_id,status,updated_at) para supervisión; reservas (institution_id,target_account_id) WHERE state='ACTIVE'; jobs (available_at,id) WHERE state='READY'; (lease_until) WHERE state='LEASED'; auditoría (institution_id,deposit_id,aggregate_version); idempotencia (response_expires_at) WHERE phase='RESPONDED'.

Migraciones versionadas, revisables y probadas desde base vacía y versión anterior; no usar create_all como despliegue productivo. No instalar extensiones UUID obligatorias: generar UUIDv4 en aplicación o función disponible, sin alterar identidad API. Definir constraints e índices explícitamente en migración. Validar datos antes de endurecer constraints; no convertir un antiguo FAILED_REVERSED en REJECTED sin conciliar evidencia externa.

Rol runtime: sin DDL y sin UPDATE/DELETE de auditoría. Rol migrador separado. Ningún borrado en cascada de depósitos, auditoría o claves. Una tarea con privilegios específicos ejecuta sólo la retención autorizada.

## 3. Transacciones y orden de bloqueos (DAT-003)

Nivel READ COMMITTED con bloqueos explícitos. Toda ruta que reserva, libera o convierte cupo toma primero account_limit_locks, después depósito/reserva, después job. Idempotencia se inserta/resuelve en transacción corta separada cuando sólo se identifica solicitud; evitar tomarla después de account lock en otra ruta.

Crear la fila de bloqueo con INSERT ... ON CONFLICT DO NOTHING y luego SELECT ... FOR UPDATE. Todas las réplicas usan la misma base. No hay llamadas HTTP dentro de una transacción de DB. lock_timeout=500 ms y statement_timeout=2 s para solicitudes; dos reintentos de transacción con jitter 25..100 ms, dentro del presupuesto total; si sigue bloqueada, continuar por job durable o 503 si no hubo aceptación.

### T1 — Registrar petición

Insertar clave única PROCESSING, depósito RECEIVED, evidencia única, evento inicial versión 1 y job VALIDATE en un commit. Si colisiona clave, rollback y resolver replay/conflicto leyendo registro ganador. Si colisiona origen, rollback entero y devolver ERR_ORIGIN_ALREADY_USED. Nunca una clave huérfana por validación fallida.

Validación estructural/auth precede T1; las validaciones de negocio posteriores generan rechazo durable. El job queda READY y disponible tras vencer lease si API adquiere trabajo inline.

### T2 — Validar y reservar

T2a: después de reclamar el job y antes de evaluar negocio o llamar a Cuentas, confirmar RECEIVED → VALIDATING en transacción corta con expected_version y owner/generation vigente; incrementar version y auditar. La recuperación sin reserva ni envío confirma PENDING_RECONCILIATION → VALIDATING del mismo modo. Si ya está VALIDATING, no repetir transición ni auditoría. Un fallo de auditoría revierte esta transacción y deja el job recuperable por lease. No adquirir reserva en T2a.

Confirmar reglas locales y cuenta fuera de locks; después tomar account lock, releer estado/version y sumar cupo en instante t usando reloj de DB. Si cabe: crear reserva ACTIVE, cambiar PENDING_CREDIT, auditar y configurar job CREDIT en el mismo commit. Si no cabe: REJECTED, auditar y cerrar job. La consulta previa de Cuentas no garantiza elegibilidad futura: el crédito la revalida.

Cálculo normativo:
```sql
-- Ejecutar sólo después de bloquear la fila de la cuenta.
SELECT COALESCE(SUM(amount), 0) FROM usd_deposits
WHERE institution_id = :institution AND target_account_id = :account
  AND status = 'COMPLETED'
  AND completed_at > :t - INTERVAL '24 hours' AND completed_at <= :t;
SELECT COALESCE(SUM(amount), 0) FROM deposit_limit_reservations
WHERE institution_id = :institution AND target_account_id = :account
  AND state = 'ACTIVE';
```
Sumar ambos resultados y nuevo amount; rechazar sólo si supera política. No usar fecha de creación para consumo confirmado.

### T3 — Preparar intento externo

Reclamar job y commit de lease antes de red. Registrar started_at antes del envío. Establecer PENDING_CREDIT antes del crédito y conservar referencia. Si caída deja intento sin finished_at, tratarlo UNKNOWN y consultar referencia antes de reenviar.

### T4 — Aplicar resultado

Con account lock y control de versión/generation: SUCCESS validado → COMPLETED, tx_id real, credited_at externo, completed_at de DB, reserva CONSUMED, auditoría y job DONE en un commit. completed_at es instante de confirmación local para límite móvil; credited_at documenta instante contable externo.

REJECTED externo definitivo o validación local fallida → REJECTED, error_code, reserva RELEASED si existía, auditoría, job DONE. Resultado incierto → PENDING_RECONCILIATION, auditoría y job READY con próximo intento, reserva sin liberar.

### T5 — Guardar respuesta HTTP

Persistir respuesta inicial y headers Location/Retry-After junto al vínculo de idempotencia. Si terminalización ocurrió en presupuesto puede compartirse T4; si se devuelve 202 debe guardarse antes de escribir en socket. Actualización compare-and-set de PROCESSING a RESPONDED: primer escritor gana; API lee y envía esa respuesta, no una representación diferente calculada después. Crash anterior a T5: worker/sweeper finaliza con 202 si pendiente, 201 si completado o Problem Details terminal si rechazado; competidores ven IN_PROGRESS hasta entonces. No dejar PROCESSING más de 60 s sin recuperación automática.

Cada 10 s el worker examina claves PROCESSING de más de 30 s, incluso si job está DONE, para reparar resultado inicial. Verifica vínculo y estado del depósito en transacción corta antes del compare-and-set. Nunca reinicia un depósito por falta de respuesta. response_expires_at=responded_at+24 h; compactor sólo convierte a TOMBSTONE si terminal y vencida.

### T6 — Solicitar conciliación

Validar identidad y body, resolver ámbito RECONCILE de clave y hash del reason/deposit_id. En transacción corta bloquear depósito y job sin tocar reserva: comprobar no terminal, no LEASED y ausencia de solicitud manual activa; insertar idempotencia, reconciliation_requests QUEUED, adelantar/reactivar job existente y guardar respuesta 202 en el mismo commit. No tomar account lock porque no cambia cupo; no intentar adquirirlo después de bloquear depósito. Si hay carrera terminal, rollback y 409. Colisiones de clave resuelven replay/conflicto; rechazos sin aceptación no reservan clave de conciliación.

## 4. Workers concurrentes (DAT-004)

Reclamar lotes <=20 con FOR UPDATE SKIP LOCKED; incrementar generation y attempt_count, asignar lease de 30 s, commit; ejecutar red fuera de locks. Renovar cada 10 s si sigue activo. Sólo owner/generation vigente puede aplicar resultado. Expiración permite reclamar, consultar referencia y recuperar; una respuesta tardía no puede sobrescribir estado terminal ni generación nueva.

Auditoría registra transición con versión incremental, no cada retry si no cambia estado. Repetir una transición terminal idéntica es no-op; evidencia conflictiva genera alarma y revisión. Queda prohibido confiar únicamente en un mutex Python.

## 5. Trabajos durables y evolución

processing_jobs actúa como cola transaccional PostgreSQL en v1, tanto para completar como conciliar. No se requiere broker. Si se añaden eventos a consumidores externos, incorporar outbox_events (UUID, institución, aggregate_id, aggregate_version, type, payload mínimo, created_at, published_at, attempt_count) en el mismo commit que la transición. Publicación al menos una vez; consumidor deduplica event_id. No prometer entrega exactamente una vez ni crear dependencia de broker en v1.

Retención y backups: SPEC-05/08. Bases de prueba deben demostrar restricciones y recuperación, no sólo tablas similares en SQLite.

## 6. Anonimización y archivo (DAT-005)

Añadir pii_anonymized_at TIMESTAMPTZ nullable a usd_deposits y reason_anonymized_at TIMESTAMPTZ nullable a reconciliation_requests. Antes de anonimizar, origin_details es objeto conforme a la variante original; después es exactamente {}, aml_declaration y notes son NULL. La tarea no cambia version, updated_at ni evidencia separada de deduplicación; registra ejecución en auditoría administrativa de retención, sin insertar una transición ficticia del agregado. reason es VARCHAR(500) nullable únicamente cuando reason_anonymized_at no es NULL; al anonimizar queda NULL. La entrada pública reason sigue siendo obligatoria, no nullable y de 10..500 caracteres.

En v1, conservar registros técnicos terminales más allá de 365 días como archivo lógico de la misma base, consultable y sujeto a los mismos permisos; 365 días es retención mínima, no borrado automático. Mantener indefinidamente, hasta una futura decisión de purga coordinada, las claves de idempotencia TOMBSTONE (ámbito, hash y vínculo), la unicidad de origen y las referencias contables. No hay FK rota ni archivo externo en v1. T1 consulta estas restricciones también después de 365 días. La política productiva de conservación debe ratificarse en EXT-04; cualquier purga posterior exige migración, consulta de deduplicación equivalente y escenarios nuevos.

Referencia de mecanismo: [bloqueos explícitos PostgreSQL](https://www.postgresql.org/docs/current/explicit-locking.html). Las fronteras transaccionales de esta spec son decisiones del proyecto.
