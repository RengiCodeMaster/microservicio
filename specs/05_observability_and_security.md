# SPEC-05 — Seguridad, privacidad y observabilidad

Versión: 2.1. SEC y OBS son requisitos implementables; identidades concretas de producción se inyectan según SPEC-08/09.

## 1. Identidad y autorización (SEC-001)

JWT firmado RS256 mediante issuer/JWKS configurados; comprobar firma, algoritmo permitido, iss, aud=usd-deposits, exp, nbf y sub no vacío. Tolerancia de reloj máxima 30 s; no aceptar none ni algoritmo indicado sin allowlist. Claims: institution_id, roles array, scope string, authorized_channels array y authorized_origins array para creadores. client exige authorized_account_ids array confiable; ausencia niega acceso. Tokens emitidos exclusivamente por proveedor confiable, no por esta API.

JWKS cache 15 min, recargar una vez ante kid desconocido; si no puede verificar token negar acceso. No registrar token ni kid como label de métricas. Cambios de permisos de cliente dependen de vigencia del token: máximo 5 min propuesto, renovación por proveedor. La credencial de Cuentas es independiente, de servicio, y aplica aislamiento por institución.

| Rol | Scope | Permiso |
| --- | --- | --- |
| teller | deposits:create, deposits:read | Crear BRANCH y leer recursos de orígenes autorizados en su institución. |
| system | deposits:create, deposits:read | Crear ATM/PARTNER y leer recursos de sus orígenes autorizados. |
| client | deposits:read | Leer exclusivamente target_account_id en authorized_account_ids. |
| operations | deposits:read, deposits:reconcile | Leer y conciliar recursos de su institución. Sin crear ni forzar estados. |

Si token tiene varios roles, unión de permisos sin cruzar institución. Lectura teller/system exige coincidencia origin_issuer en authorized_origins. API revalida institución y ámbito también en replay, comprobante e historial. Consulta de cuenta fuera del ámbito no divulga existencia. No confiar en X-Channel como prueba de permiso.

Creación teller/system puede dirigirse a cualquier cuenta de su institución: antes de T1 comprobar rol/canal/origen; antes de reservar, Cuentas confirma institution_id y se niega con 404 si no coincide. client y operations no crean. No existe claim aportado por el body que amplíe la institución. Si se restringen cuentas por emisor en una integración posterior, añadir ese permiso al contrato antes de implementarlo.

El rechazo posterior a T1 se conserva conforme a DOM-016. Para replay, comprobar primero permisos actuales de creación y visibilidad local por institución/origen: rol/scope/canal revocado produce 403; depósito ya no visible por origen produce 404 ERR_DEPOSIT_NOT_FOUND sin body/Location previos. Esta comprobación precede conflicto, IN_PROGRESS, EXPIRED y replay. No consultar Cuentas para repetir una respuesta guardada ni revelar que existe una clave fuera del ámbito del actor.

Para clave nueva, autorizar el emisor de la variante del body (branch_id, atm_id o source_bank_id) contra authorized_origins antes de T1, incluso si luego se rechaza compatibilidad tipo/canal. La restricción teller→BRANCH y system→ATM/PARTNER se mantiene para canales habilitados. Si un rol creador con deposits:create tiene WEB/MOBILE en authorized_channels, devolver el rechazo durable DOM-017 antes de aplicar esa restricción rol/canal; no hay origen específico WEB/MOBILE, pero la variante de evidencia aportada sí debe estar autorizada. Un token sin rol creador/scope/claim del canal devuelve 403.

health/live y health/ready accesibles por red interna sin JWT; no muestran credenciales/URLs. /metrics sólo red de monitorización, no público. Docs/OpenAPI públicos únicamente en local; producción requiere red interna.

## 2. Datos y retención (SEC-002)

TLS para API/Cuentas/DB en producción; cifrado de discos/backups y secretos mediante gestor del entorno. No poner claves o DSN reales en repositorio. Usar consultas parametrizadas. Rechazar campos extra; límites de body/texto conforme a SPEC-02.

Logs: no guardar nombre/documento, origen completo, AML, notes, reason de conciliación, token, payload ni balance. Cuenta enmascarada mostrando últimos cuatro caracteres; preferir deposit_id para trazas internas. Respuestas de error no reflejan datos de entrada.

Propuesta de retención académica: depósitos, auditoría, referencias y vínculos de idempotencia mínimo 365 días desde estado terminal, seguidos de archivo lógico sin purga automática en v1; PII en origin_details/AML/notes se anonimiza a los 30 días terminales según DAT-005. reason de conciliación se elimina 30 días después de finished_at, incluso si su solicitud terminó MANUAL_REVIEW y el depósito sigue pendiente; conservar actor, fechas y estado técnico. Logs 30 días; métricas agregadas 90 días; backups 30 días. Pendientes no se purgan; su origen/AML/notes se conserva hasta el plazo terminal. No afirmar validez bancaria de estos plazos: producción requiere política aprobada de institución/jurisdicción (DEC-07).

Anonimización no altera monto/estado/referencia/versiones ni auditoría. El hash idempotente permanece, aunque PII desaparezca. Las claves, evidencias y referencias se conservan sin vencimiento automático conforme a DAT-005; no se asume un plazo externo desconocido. Una decisión futura de purga debe acordar con Cuentas y canales cuándo el origen deja de reaparecer. Acceso a PII sólo rol interno de cumplimiento separado, sin endpoint público v1; cada lectura administrativa se audita.

## 3. Protección de abuso (SEC-003)

Rate limit propuesto por institution_id/sub: crear 60/min, conciliar 10/min, lecturas 300/min; ráfaga hasta cuota indicada. Implementar en gateway compartido o almacén común, no contador por proceso. 429 con Retry-After calculado hasta siguiente ventana. Límites de transporte pueden aplicarse antes de auth para proteger recursos; no divulgar identidad.

Sin cookies de sesión; no se exige CSRF en autenticación Bearer. CORS deshabilitado en v1 sin frontend; habilitar sólo lista explícita si aparece consumidor navegador. Usuario runtime sin privilegios; separar rol DB migraciones/runtime; SQL y auditoría conforme a SPEC-03.

## 4. Logs y trazas (OBS-001)

Cada línea JSON: timestamp UTC, level, service=usd-deposits, environment, event, correlation_id, deposit_id cuando existe, channel cuando aplica, status o safe_error_code y elapsed_ms. Registro de inicio/fin HTTP, transiciones, llamadas externas y recuperación de leases. Eventos no equivalen a auditoría durable.

Correlation inválido genera uno nuevo para el error y devuelve 400. En jobs usar correlation original; intento manual agrega request_correlation_id. Soportar propagación traceparent si hay tracing; no usar correlation como autorización. No exponer excepción cruda.

## 5. Métricas (OBS-002)

| Métrica | Tipo | Labels acotados / significado |
| --- | --- | --- |
| usd_deposits_http_requests_total | Counter | route plantilla, method, status_code; incluye replay. |
| usd_deposits_admitted_total | Counter | channel, deposit_type; una admisión por depósito. |
| usd_deposits_completed_total | Counter | channel; una confirmación local por depósito. |
| usd_deposits_rejected_total | Counter | code; rechazo durable. |
| usd_deposits_http_duration_seconds | Histogram | route plantilla, method, status_code. |
| accounts_service_call_duration_seconds | Histogram | operation, outcome. |
| accounts_service_circuit_breaker_state | Gauge | Sin label state: valor 0=CLOSED,1=HALF_OPEN,2=OPEN. |
| usd_deposits_pending_jobs | Gauge | kind, state; cantidad actual desde DB. |
| usd_deposits_oldest_pending_seconds | Gauge | kind; edad del más antiguo. |
| usd_deposits_reserved_amount_usd | Gauge | Total de reservas activas, sin cuenta/institución como labels. |

No labels con cuenta, cliente, UUID, correlation, URL concreta ni texto libre. Métricas de runtime son operativas y pueden perder incrementos en crash; informes financieros se calculan desde DB, nunca desde counters flotantes. Exponer formato Prometheus en /metrics.

## 6. Alertas y auditoría (OBS-003)

Alerta inmediata: MANUAL_REVIEW, evidencia externa conflictiva, generación que intenta alterar terminal, credencial externa rechazada. Alerta tras 5 min: edad pendiente >300 s, breaker abierto continuo, >5% errores 5xx con >=100 requests/5 min, o DB no disponible. Umbrales configurables y documentados.

Auditoría append-only: transición, versión, actor humano/worker, acción, correlation, razón segura y fecha de DB. Registrar solicitudes manuales de conciliación aparte del cambio de estado. Auditoría creada en mismo commit del efecto local; un fallo de inserción revierte operación local. No usar log stdout como sustituto.
