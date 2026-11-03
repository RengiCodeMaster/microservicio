# SPEC-02 — Contratos HTTP y Problem Details

Versión: 2.1. Se conserva el nombre histórico del archivo. El formato se basa en RFC 9457, que sustituye RFC 7807.

## 1. Transporte (API-001)

Base /api/v1; JSON UTF-8, TLS fuera de local. Respuestas financieras Cache-Control: no-store. Body <=32 KiB. Errores application/problem+json. No redirigir automáticamente POST.

| Header | Obligación |
| --- | --- |
| Authorization: Bearer … | Toda ruta de negocio. |
| Content-Type: application/json | Peticiones con body; otro valor 415. |
| X-Idempotency-Key | UUIDv4 en crear y conciliar; ámbitos separados. |
| X-Channel | Sólo crear, requerido y autorizado contra token. |
| X-Correlation-ID | UUIDv4 opcional; generar si falta; inválido 400; siempre devolver. |

UUIDs se normalizan a minúsculas. Fechas RFC 3339 UTC con Z y milisegundos. Dinero string decimal con dos decimales, parte entera 1..13 dígitos sin ceros iniciales salvo 0. No aceptar número JSON, exponente, signo ni espacios. Rechazar JSON con claves repetidas y propiedades desconocidas recursivamente. Null sólo en campos explícitamente nullable. Identificadores genéricos ASCII [A-Za-z0-9_-], 1..64; texto libre sin controles, con al menos un carácter no blanco.

## 2. Crear (API-002)

POST /api/v1/deposits/usd.

| Campo | Contrato |
| --- | --- |
| target_account_id | Requerido, string ^ACC-[A-Z]{3}-[0-9]{8}$. Etiqueta no prueba moneda. |
| amount | String requerida, formato monetario y reglas DOM-007..011. |
| currency | Literal USD requerido. |
| deposit_type | DEP_CASH_USD o DEP_TRANSFER_USD requerido. |
| origin_details | Objeto requerido según variante. |
| aml_declaration | Opcional; objeto si presente, nunca null. |
| notes | Opcional 1..500 caracteres, nunca null. |

Efectivo: depositor_id_type DNI/PASSPORT, depositor_id_number alfanumérico 1..32, depositor_full_name 1..150, physical_receipt_id 1..64. DNI exige ocho dígitos. BRANCH exige branch_id y teller_id; ATM exige atm_id. Los campos de otra variante se prohíben. teller_id coincide con sub, sucursal/ATM con claim authorized_origins.

Transferencia: source_bank_id, bank_reference (1..64), exactamente uno entre routing_number (9 dígitos) y swift_code (8 u 11 alfanuméricos; primeras 6 letras mayúsculas). Sólo validación de forma, sin checksum ni verificación del banco. No se admiten campos físicos.

AML: aml_form_id 1..64 y funds_source enum SALARY/BUSINESS/SAVINGS/OTHER requeridos. OTHER exige description 1..256, prohibida para los demás. Si amount >=10000.00 y no hay declaración: ERR_AML_DECLARATION_REQUIRED.

```json
{
  "target_account_id": "ACC-USD-88992211",
  "amount": "1500.50",
  "currency": "USD",
  "deposit_type": "DEP_CASH_USD",
  "origin_details": {
    "depositor_id_type": "DNI",
    "depositor_id_number": "74883321",
    "depositor_full_name": "Carlos Gomez",
    "physical_receipt_id": "RCPT-000001",
    "branch_id": "BR-01",
    "teller_id": "USER-TL-509"
  }
}
```

201 sólo COMPLETED confirmado dentro de presupuesto HTTP de 8 s; 202 cuando queda pendiente durable. Ambos incluyen Location: /api/v1/deposits/usd/{deposit_id}; 202 incluye Retry-After: 5. Agotar tiempo no cancela abono potencial. Fallo de DB previo a commit: 503. Commit de resultado incierto: cliente reintenta misma clave. Nunca responder éxito antes de commit.

Representación Deposit común para POST y GET: deposit_id (dep_usd_<UUIDv4>), target_account_id, amount, currency, deposit_type, channel, status, fee_applied (siempre "0.00"), net_credited_amount (amount sólo COMPLETED, null en otros estados), account_service_tx_id (string 1..128 o null), correlation_id original, created_at, updated_at, completed_at (fecha o null), receipt_url (ruta o null), error_code (catálogo o null). Todos aparecen. Sólo COMPLETED tiene tx_id, completed_at y receipt_url no nulos. No divulgar notes/origen/AML.

```json
{
  "deposit_id": "dep_usd_7f9c8d6e-9311-4702-861a-0e9b97b0a884",
  "target_account_id": "ACC-USD-88992211",
  "amount": "1500.50",
  "currency": "USD",
  "deposit_type": "DEP_CASH_USD",
  "channel": "BRANCH",
  "status": "COMPLETED",
  "fee_applied": "0.00",
  "net_credited_amount": "1500.50",
  "account_service_tx_id": "ACC-TX-55441199",
  "correlation_id": "c8a16dbb-7a32-4d2b-a4ff-3bcf91280332",
  "created_at": "2026-10-13T15:00:00.000Z",
  "updated_at": "2026-10-13T15:00:01.000Z",
  "completed_at": "2026-10-13T15:00:01.000Z",
  "receipt_url": "/api/v1/deposits/usd/dep_usd_7f9c8d6e-9311-4702-861a-0e9b97b0a884/receipt",
  "error_code": null
}
```

Rechazo de negocio después del registro: Problem Details según catálogo con deposit_id y Location, resultado almacenado. Replay devuelve código/body/Location iniciales y X-Idempotency-Replayed: true; correlation header es de la nueva petición, body conserva el original. 202 guardado no cambia a 201: consultar GET.

Revalidar permisos actuales antes de resolver cualquier resultado de idempotencia según SEC-001. Cuenta inexistente o de otra institución detectada después de T1 genera el rechazo local seguro DOM-016. WEB/MOBILE y compatibilidad tipo/canal se evalúan según DOM-017: el schema estructural acepta una variante completa de origen por deposit_type; la compatibilidad entre variante y X-Channel es validación de negocio posterior a T1. Para efectivo se exige exactamente una variante física completa BRANCH o ATM; no mezclar ambas. PARTNER exige que source_bank_id figure en authorized_origins.

## 3. Consulta e historial (API-003)

GET /api/v1/deposits/usd/{deposit_id}: 200 Deposit; ID mal formado 400; inexistente o no visible 404 ERR_DEPOSIT_NOT_FOUND.

GET /api/v1/deposits/usd: target_account_id opcional, status opcional enum SPEC-01, limit entero 1..100 default 20, offset entero >=0 default 0. Filtros desconocidos/repetidos 400. client debe enviar target_account_id autorizado; otros roles listan sólo su ámbito. Orden created_at DESC, id DESC. total/items en snapshot común; no garantiza snapshot entre páginas.

Salida: {"items":[…],"pagination":{"total":1,"limit":20,"offset":0}}. Item: deposit_id, target_account_id, amount, currency, status, created_at. Sin resultados items=[], total=0. Filtros no autorizados se responden 404 sin revelar existencia.

## 4. Comprobante (API-004)

GET /api/v1/deposits/usd/{deposit_id}/receipt: 200 JSON sólo COMPLETED; 409 ERR_RECEIPT_NOT_AVAILABLE si visible pero no completado; 404 si no visible. Campos: receipt_id igual deposit_id, deposit_id, target_account_id, amount, currency, fee_applied, net_credited_amount, channel, deposit_type, account_service_tx_id, completed_at. Inmutables. Sin PII del depositante. PDF fuera de v1.

## 5. Conciliación (API-005)

POST /api/v1/deposits/usd/{deposit_id}/reconcile: operations con scope deposits:reconcile. Body {"reason":"Verificación solicitada por soporte"}, reason 10..500 requerida. No acepta monto, cuenta, estado deseado ni referencia nueva.

202 {"reconciliation_id":"<UUIDv4>","deposit_id":"dep_usd_…","status":"QUEUED"}, Location al depósito, Retry-After: 5. Clave/body idénticos repiten respuesta; distinto hash 409. Job LEASED o solicitud manual QUEUED/RUNNING previa: 409 ERR_RECONCILIATION_IN_PROGRESS. Job READY sin solicitud manual activa puede adelantarse a available_at=ahora; MANUAL_REVIEW puede reactivarse. Siempre reutilizar el job, nunca crear ejecución paralela. Estado terminal: 409 ERR_DEPOSIT_TERMINAL. Registrar actor y reason de forma privada.

## 6. Errores (API-006)

Campos requeridos: type="urn:usd-deposits:problem:<code>", title estable en español, status igual HTTP, detail seguro, instance ruta sin query sensible, code, correlation_id y timestamp UTC. Opcionales deposit_id y errors=[{"pointer":"/amount","code":"INVALID_FORMAT","detail":"Formato monetario inválido"}]. No reflejar datos personales, tokens, stacktrace o respuesta externa cruda.

| HTTP | Código | Causa |
| --- | --- | --- |
| 400 | ERR_INVALID_REQUEST | JSON, headers, ruta o query inválidos. |
| 401 | ERR_UNAUTHENTICATED | Token ausente/inválido/vencido; WWW-Authenticate: Bearer. |
| 403 | ERR_FORBIDDEN | Rol, scope, canal u origen no autorizado. |
| 404 | ERR_DEPOSIT_NOT_FOUND | Depósito inexistente/no visible. |
| 404 | ERR_ACCOUNT_NOT_FOUND | Cuenta inexistente, después de validar ámbito. |
| 409 | ERR_IDEMPOTENCY_CONFLICT | Hash distinto. |
| 409 | ERR_IDEMPOTENCY_IN_PROGRESS | Resultado inicial no guardado; Retry-After: 1. |
| 409 | ERR_IDEMPOTENCY_EXPIRED | Sólo queda vínculo histórico; Location si visible. |
| 409 | ERR_ORIGIN_ALREADY_USED | Evidencia ya registrada. |
| 409 | ERR_RECEIPT_NOT_AVAILABLE | No completado. |
| 409 | ERR_RECONCILIATION_IN_PROGRESS | Trabajo activo. |
| 409 | ERR_DEPOSIT_TERMINAL | No admite nueva conciliación. |
| 413 | ERR_PAYLOAD_TOO_LARGE | Body excede 32 KiB. |
| 415 | ERR_UNSUPPORTED_MEDIA_TYPE | Content-Type inválido. |
| 422 | ERR_VALIDATION | Campo/tipo/formato de body inválido. |
| 422 | ERR_CHANNEL_NOT_SUPPORTED | WEB/MOBILE reservados. |
| 422 | ERR_DEPOSIT_AMOUNT_LIMIT | Fuera de límites por canal. |
| 422 | ERR_AML_DECLARATION_REQUIRED | Falta declaración requerida. |
| 422 | ERR_DAILY_LIMIT_EXCEEDED | Cupo insuficiente. |
| 422 | ERR_ACCOUNT_FROZEN | Cuenta congelada. |
| 422 | ERR_ACCOUNT_INACTIVE | No ACTIVE. |
| 422 | ERR_ACCOUNT_DEPOSITS_DISABLED | No admite depósitos. |
| 422 | ERR_ACCOUNT_CURRENCY_MISMATCH | No admite USD. |
| 422 | ERR_CREDIT_REJECTED | Rechazo definitivo externo restante. |
| 429 | ERR_RATE_LIMITED | Límite de solicitudes; Retry-After. |
| 500 | ERR_INTERNAL | Fallo inesperado con detalle seguro. |
| 503 | ERR_DATABASE_UNAVAILABLE | Persistencia indisponible. |
| 503 | ERR_ACCOUNTS_SERVICE_UNAVAILABLE | Dependencia inaccesible sin aceptación durable. |

Errores de autenticación/estructura no consumen clave. Fallo externo tras aceptación durable produce 202, no rechazo financiero. Consulta de cuenta devuelve errores de negocio sólo con respuesta válida. No convertir respuesta externa desconocida en REJECTED.

## 7. Cuentas: contrato obligatorio (INT-001)

Credencial de servicio, ámbito de institución autenticado y correlation header en toda llamada. deposit_reference es deposit_id completo, estable. Todos los montos son strings decimales.

GET /api/v1/accounts/{account_id}: 200 con account_id, institution_id, customer_id, status, currency, allows_deposits, is_frozen; MULTI_CURRENCY agrega enabled_currencies. 404 inexistente. Ausencia/tipos inválidos: fallo contractual.

Validar account_id contra la ruta y tipos de todos los campos: identificadores string no vacíos con longitudes de DAT-001, status enum ACTIVE/INACTIVE/CLOSED, currency MULTI_CURRENCY o tres letras ASCII mayúsculas, flags booleanos, enabled_currencies array de códigos de tres letras ASCII mayúsculas únicos cuando corresponde. Moneda distinta de USD sin habilitación USD produce ERR_ACCOUNT_CURRENCY_MISMATCH. Un institution_id distinto produce DOM-016 sin divulgar datos externos. GET cuenta 404 válido usa application/problem+json con code=ACCOUNT_NOT_FOUND, account_id igual a la ruta y status=404; otro body no prueba inexistencia.

POST /api/v1/accounts/{account_id}/credits: body {"deposit_reference":"dep_usd_…","amount":"1500.50","currency":"USD","channel":"BRANCH","source_system":"MS_DEPOSITS_USD","concept":"Depósito USD"}. X-Idempotency-Key igual deposit_reference. Unicidad por institución/source_system/referencia durante vida contable. Mismo contenido repite transacción; contenido distinto 409 sin nuevo efecto. Cuentas valida elegibilidad y asiento atómicamente.

200/201: transaction_id, deposit_reference, account_id, credited_amount, currency, status=SUCCESS y credited_at UTC. Confirmar identidad, monto y moneda; incoherencia mantiene pendiente. No se necesita new_balance.

GET /api/v1/accounts/{account_id}/credits/by-reference/{deposit_reference}: lectura autoritativa. 200 SUCCESS con campos anteriores, o 200 REJECTED con el objeto definitivo descrito abajo; 202 con {"status":"PROCESSING","deposit_reference":"dep_usd_…","account_id":"ACC-USD-88992211","institution_id":"INST-01","source_system":"MS_DEPOSITS_USD"}; 404 application/problem+json con status=404, code=CREDIT_REFERENCE_NOT_FOUND y la misma identidad de referencia/cuenta/institución/source_system. Verificar estos campos contra la solicitud y credencial. Rechazo definitivo se conserva por referencia e impide crédito posterior.

### Rechazo definitivo de crédito (INT-002)

POST crédito responde 404 para ACCOUNT_NOT_FOUND y 422 para los demás códigos de la tabla, con Content-Type application/json y este objeto completo; lookup devuelve el mismo objeto con 200. No basta el código HTTP para liberar cupo.

```json
{
  "status": "REJECTED",
  "deposit_reference": "dep_usd_7f9c8d6e-9311-4702-861a-0e9b97b0a884",
  "account_id": "ACC-USD-88992211",
  "institution_id": "INST-01",
  "source_system": "MS_DEPOSITS_USD",
  "requested_amount": "1500.50",
  "currency": "USD",
  "rejection_code": "ACCOUNT_FROZEN",
  "finalized_at": "2026-10-13T15:00:01.000Z"
}
```

Todos los campos son requeridos, no nullable y sin propiedades extra. Referencia, cuenta, institución, source_system, monto y moneda deben coincidir exactamente con el crédito persistido; finalized_at sigue el formato UTC de API-001. Cuentas guarda el rechazo atómicamente bajo la misma unicidad que el crédito: no existe asiento para esa referencia ni puede crearse posteriormente, incluso si cambia la elegibilidad. Un código desconocido, identidad distinta, schema inválido o HTTP no permitido es ContractFailure: conservar reserva y pasar a MANUAL_REVIEW, nunca REJECTED.

| rejection_code externo | Error local | HTTP público inicial si aún no se guardó respuesta |
| --- | --- | --- |
| ACCOUNT_NOT_FOUND | ERR_ACCOUNT_NOT_FOUND | 404 |
| ACCOUNT_FROZEN | ERR_ACCOUNT_FROZEN | 422 |
| ACCOUNT_INACTIVE | ERR_ACCOUNT_INACTIVE | 422 |
| DEPOSITS_DISABLED | ERR_ACCOUNT_DEPOSITS_DISABLED | 422 |
| CURRENCY_NOT_SUPPORTED | ERR_ACCOUNT_CURRENCY_MISMATCH | 422 |
| CREDIT_POLICY_REJECTED | ERR_CREDIT_REJECTED | 422 |

POST crédito 400 es error de contrato y no rechazo definitivo en v1. 401/403 son errores de credencial, 409 conflicto contractual y 5xx/timeout resultado incierto según RES-002. No se reflejan mensajes externos en detail público. Si T5 ya guardó 202, no reemplazarlo por el error posterior; GET presenta REJECTED y error_code local. SUCCESS debe incluir también institution_id y source_system coincidentes tanto en POST como lookup; transaction_id string 1..128 y credited_at UTC requeridos.

Un 404 de lookup con CREDIT_REFERENCE_NOT_FOUND no demuestra ausencia definitiva mientras pueda haber llamada en vuelo; difiere del 404 de POST con rechazo irreversible ACCOUNT_NOT_FOUND validado por INT-002. Reenvío sólo con misma referencia después de lookup válido. Sin idempotencia y lookup externo no se considera segura ni aceptada la integración; el mock debe implementar este contrato.

## 8. Entregable de contrato

Antes de rutas, derivar openapi.yaml OpenAPI 3.1 con schemas, variantes oneOf, headers, security, ejemplos y respuestas. Validarlo con ejemplos y usarlo en pruebas. Markdown es fuente normativa en esta fase; OpenAPI es entregable posterior, aún no generado.

Fuentes: [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457), [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785). Las políticas particulares de esta API son decisiones del proyecto.
