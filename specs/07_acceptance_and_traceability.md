# SPEC-07 — Aceptación y trazabilidad

Versión: 2.1. Escenarios normativos; todavía no ejecutados contra la nueva definición.

## 1. Preparación y criterios (QA-001)

Usar reloj controlado, cuentas USD/MULTI_CURRENCY/no USD, tokens por rol/institución y mock INT-001 con ledger durable y contador de abonos efectivos. Cada prueba usa esquema PostgreSQL aislado; pruebas de concurrencia usan conexiones distintas, idealmente procesos distintos. Verificar HTTP, persistencia, auditoría, reservas, jobs y ledger externo.

Todas las pruebas críticas siguientes deben pasar. Meta secundaria: >=90% cobertura de ramas en dominio/aplicación; no equivale a seguridad financiera. No exigir ese porcentaje a código generado/adaptadores triviales como sustituto de escenarios.

## 2. Matriz Given / When / Then

| ID | Dado / cuando | Resultado obligatorio | Requisitos |
| --- | --- | --- | --- |
| AC-01 | teller BRANCH autorizado, cuenta activa USD, 1500.50 con origen único | 201 COMPLETED, un abono, reserva CONSUMED, auditoría de cada transición, comprobante estable. | DOM-001..006, API-002/004 |
| AC-02 | Política inicial, probar 0.99/1.00 y 5000.00/5000.01 en ATM | 0.99 y 5000.01 rechazados; valores inclusivos aceptados con cupo. | DOM-007/009 |
| AC-03 | Tres fixtures independientes BRANCH con cuenta elegible y cupo vacío: 9999.99, 10000.00 sin AML, 10000.00 con AML válido | Primero admitido, segundo 422, tercero admitido con cupo. | DOM-011 |
| AC-04 | Fixtures independientes BRANCH 50000.00 y 50000.01, AML válido, cuenta elegible, actor/origen autorizado y sin consumo/reservas previos | Primero 422 ERR_DAILY_LIMIT_EXCEEDED, segundo 422 ERR_DEPOSIT_AMOUNT_LIMIT; sin abono. | DOM-008/010/011 |
| AC-05 | Consumo confirmado 19000.00; crear 1000.00 y luego 1.00 adicional a cupo lleno | Igualdad admitida; segundo depósito 422 DAILY_LIMIT_EXCEEDED, sin crédito adicional. | DOM-007/010 |
| AC-06 | Consumo completed_at exactamente t−24 h / 1 ms posterior | Exacto excluido, posterior incluido; created_at no altera cálculo. | DOM-010, DAT-003 |
| AC-07 | Reserva UNKNOWN de más de 24 h | Sigue consumiendo cupo; no liberar por edad. | DOM-005/010 |
| AC-08 | Cuenta congelada/inactiva/sin depósitos/no USD, cada variante | Error específico; REJECTED y cero abonos/reservas activas. | DOM-012, API-006 |
| AC-09 | MULTI_CURRENCY con/sin USD habilitado | Admitir sólo con sub saldo USD habilitado. | DOM-012 |
| AC-10 | Cuentas cambia elegibilidad después del GET y antes del crédito | Crédito rechaza atómicamente; reserva liberada sólo con rechazo definitivo. | INT-001, DAT-003 |
| AC-11 | Mismo body/clave después de resultado inicial | Mismo código/body/Location; replay header; ledger con un abono. | DOM-013, API-002 |
| AC-12 | Mismo body con propiedades reordenadas / notes o AML modificados | Reordenado replay; cualquier cambio semántico 409 conflicto. | DOM-013 |
| AC-13 | Dos POST simultáneos misma clave antes de respuesta persistida | Una ejecución; competidor 409 IN_PROGRESS; reintento posterior replay. | DOM-003/013, DAT-003 |
| AC-14 | Dos claves, misma evidencia de origen | Uno registrado; otro 409 ORIGIN_ALREADY_USED; un abono. | DOM-014, DAT-001 |
| AC-15 | Cupo 19000.00, dos depósitos de 1000.00 simultáneos con claves/orígenes distintos | Sólo una reserva/abono; otro rechazo por límite. | DOM-010, DAT-003 |
| AC-16 | Misma clave/hash en otra institución o sujeto | Ámbito independiente; evidencia de origen sigue siendo única por institución. | DOM-013/014, SEC-001 |
| AC-17 | Clave con respuesta >24 h, pendiente / terminal compactada | Pendiente conserva replay; compactada 409 EXPIRED, no ejecución nueva. | DOM-013 |
| AC-18 | Abono externo exitoso, respuesta perdida por timeout | 202 o replay inicial; pendiente reservado; lookup confirma y un único abono. | DOM-005, RES-004 |
| AC-19 | Crash entre abono externo y T4 | Reinicio consulta referencia y completa; no segundo abono. | DAT-003/004, RES-004 |
| AC-20 | Crash tras T1 antes de respuesta inicial | Worker recupera <=60 s, vincula resultado; misma clave no genera otra operación. | DAT-003, RES-004 |
| AC-21 | Lookup PROCESSING/404/5xx | PROCESSING espera; 404 reenvía misma referencia; 5xx retiene y reprograma. | INT-001, RES-004 |
| AC-22 | Crédito devuelve 200 con monto/cuenta/moneda/referencia incorrectos | No COMPLETED; reserva activa, revisión contractual. | DOM-004, INT-001 |
| AC-23 | Cinco fallos transitorios consecutivos | Breaker OPEN 30 s; jobs pendientes; API lista para consultas y aceptación durable. | RES-003 |
| AC-24 | Rechazo externo definitivo guardado por referencia | REJECTED, reserva RELEASED; reenvío nunca abona. | INT-001, DAT-003 |
| AC-25 | Dos workers, lease vencido y respuesta tardía del anterior | generation anterior no altera terminal; un efecto externo y auditoría consistente. | DAT-004 |
| AC-26 | 20 ciclos o 24 h de conciliación, sin evidencia final | MANUAL_REVIEW, alerta, reserva activa; no rechazo ni retry automático adicional. | RES-004, OBS-003 |
| AC-27 | operations concilia pendiente; repetir clave / conciliar terminal | 202 idempotente; terminal 409; actor/reason registrados. | API-005, SEC-001 |
| AC-28 | JWT inválido/vencido, issuer/aud/algoritmo incorrectos | 401; ninguna escritura financiera; sin información sensible. | SEC-001 |
| AC-29 | client lee cuenta ajena u otra institución por GET/lista/receipt | Sin filtración; 404 para recurso no visible; conteo filtrado; client no tiene acceso a crear/conciliar. | SEC-001, API-003 |
| AC-30 | Token WEB declara BRANCH, o teller_id distinto a sub | 403; ninguna reserva/abono. | DOM-012, SEC-001 |
| AC-31 | Rol creador, scope y canal autorizado; body de variante estructuralmente completo: efectivo PARTNER, transferencia BRANCH, o WEB/MOBILE | Tipo/canal incompatible 422 ERR_VALIDATION; WEB/MOBILE 422 ERR_CHANNEL_NOT_SUPPORTED, sin exigir origen de canal reservado; cero abonos/reservas. | DOM-017, API-002, SEC-001 |
| AC-32 | amount numérico, 1.001, exponente, null, campos extra, JSON duplicado | Formato rechazado sin redondeo; JSON duplicado 400, body inválido 422. | DOM-002, API-001 |
| AC-33 | Body >32 KiB / Content-Type incorrecto / header inválido | 413 / 415 / 400; no aceptación durable. | API-001 |
| AC-34 | Depósito pendiente consulta receipt | 409; net_credited_amount null; no comprobante financiero. | API-004 |
| AC-35 | Filtros/paginación inválidos y lista vacía | 400; lista válida vacía 200 items=[],total=0; orden estable. | API-003 |
| AC-36 | DB falla antes de T1 / después de crédito externo | Antes 503 sin operación; después recuperar lookup tras volver DB, nunca inventar reversión. | DAT-003, RES-004 |
| AC-37 | Fallo insert auditoría en transición | Rollback completo de cambio local/reserva; trabajo recuperable, sin estado parcial. | DOM-006, DAT-003 |
| AC-38 | Reiniciar mock tras acreditar; repetir referencia | Conserva tx_id y un único asiento; diferente payload 409. | RES-006, INT-001 |
| AC-39 | Logs/métricas generados por errores de validación y conciliación | Sin token/PII/payload; labels acotados; tracing/correlation presentes. | SEC-002, OBS-001/002 |
| AC-40 | Retención ejecutada con terminal de 31 días y pendiente de 31 días | Terminal anonimiza PII; pendiente no se purga; referencias/hash permanecen. | SEC-002 |
| AC-41 | Shutdown mientras hay crédito en vuelo | No liberar cupo; job recuperado por lease, referencia estable. | RES-005 |
| AC-42 | DB caída / Cuentas caída, consultar health | DB→ready 503; Cuentas sola→ready 200 degraded; live independiente. | OPS-001, RES-003 |
| AC-43 | Restore desde backup con crédito externo posterior al backup | Mantener admisión detenida; reconciliar ledger y referencias antes de reabrir. | OPS-003 |
| AC-44 | SQL intenta editar/borrar auditoría con rol runtime | Permiso denegado; lectura autorizada sigue disponible. | DAT-002, SEC-003 |
| AC-45 | Creación autorizada; GET cuenta válido informa otra institución o ACCOUNT_NOT_FOUND | REJECTED ERR_ACCOUNT_NOT_FOUND, cero reserva/crédito; inicial 404 seguro o replay 202 previo; no datos externos en GET/error. | DOM-016, API-002, SEC-001 |
| AC-46 | teller/system repite clave propia con token renovado: pierde rol/scope/canal o pierde origen | Permiso de creación revocado 403; recurso no visible por origen 404 sin body/Location previos; no nueva ejecución, incluso para conflicto/IN_PROGRESS/EXPIRED. | DOM-013, SEC-001 |
| AC-47 | POST crédito 404/422 y lookup 200: cada rechazo válido INT-002; después reenvío de referencia | Error local conforme a tabla, REJECTED, reserva RELEASED; rechazo durable y cero abonos futuros. | INT-002, DAT-003 |
| AC-48 | Rechazo externo con código desconocido, campos ausentes o monto/cuenta/institución/referencia distintos; POST 400 | No REJECTED ni liberación; PENDING_RECONCILIATION y job MANUAL_REVIEW, alerta, ninguna red automática posterior. | INT-002, RES-004 |
| AC-49 | Solicitud manual RUNNING encuentra conflicto/schema externo inválido inmediatamente | Solicitud MANUAL_REVIEW con finished_at, job MANUAL_REVIEW con last_error_code, reserva intacta; nueva solicitud reutiliza job y conserva solicitud anterior. | API-005, DAT-003, RES-004 |
| AC-50 | Worker reclama RECEIVED o pendiente sin reserva/envío; caída o fallo de auditoría durante T2a | Transición VALIDATING/version/auditoría atómicas antes de red; rollback sin transición parcial, lease recuperable, cero reserva. | DOM-015, DAT-003 |
| AC-51 | Terminal de 31 días; solicitudes DONE y MANUAL_REVIEW con finished_at de 31 días; depósito pendiente | Terminal origin_details={}, AML/notes NULL con marcador; reason NULL con marcador en solicitudes finalizadas; actor/estado/fechas/hash intactos; origen del depósito pendiente conservado. | SEC-002, DAT-005 |
| AC-52 | Depósito terminal archivado de más de 365 días; misma clave/body y nueva clave con misma evidencia | 409 ERR_IDEMPOTENCY_EXPIRED con vínculo visible y 409 ERR_ORIGIN_ALREADY_USED respectivamente; cero nuevo depósito/abono y deduplicación consultable. | DOM-013/014, DAT-005, SEC-002 |

## 3. Pruebas no funcionales (QA-002)

Carga OPS-002: verificar p95 de consultas, presupuesto de creación, cola, CPU/memoria y comportamiento degradado. No sólo medir HTTP exitoso: comprobar al final unicidad de créditos, suma de reservas y trabajos recuperados.
Contractuales: ejemplos de OpenAPI validan schemas, headers y catálogo; mock pasa contrato externo. Migraciones: base vacía y upgrade de fixture previo; backup/restauración comprobados.

## 4. Evidencia de entrega (QA-003)

Informe con commit/versión de specs, entorno, comandos, escenarios ejecutados, resultados, fallos y limitaciones. Marcar cada AC PASS/FAIL/NOT RUN. No afirmar PASS por inspección. Relacionar prueba automatizada con AC y requisitos; cualquier escenario crítico FAIL impide declarar v1 aceptada.
