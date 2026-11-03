# SPEC-01 — Dominio y reglas financieras

Versión: 2.1. Marco: [SPEC-00](00_scope_and_sdd_governance.md).

## 1. Responsabilidades e invariantes

| ID | Regla obligatoria |
| --- | --- |
| DOM-001 | Operar exclusivamente en USD, sin conversión, comisión ni intereses. Cuentas es dueño del saldo. |
| DOM-002 | Dinero con Decimal y dos decimales; no usar float ni redondear una entrada inválida. |
| DOM-003 | Cada depósito genera como máximo un abono efectivo, incluso ante reintentos y caídas. |
| DOM-004 | COMPLETED exige evidencia verificable de Cuentas y transaction_id real. Nunca fabricar un ID exitoso. |
| DOM-005 | Timeout no demuestra rechazo ni reversión; mantener resultado incierto. |
| DOM-006 | Cada transición se confirma junto con auditoría, reserva y trabajo pendiente en una transacción local. |

La solicitud procede sólo después de que el canal haya confirmado recepción física o liquidación de los fondos. El servicio no verifica billetes ni ejecuta liquidación interbancaria.

## 2. Tipos, canales y origen

Vocabulario único: BRANCH, ATM, WEB, MOBILE, PARTNER. Se elimina ATM_DEPOSIT.

| Tipo | Canales v1 | Evidencia |
| --- | --- | --- |
| DEP_CASH_USD | BRANCH, ATM | Depositante, physical_receipt_id; branch_id y teller_id en BRANCH o atm_id en ATM. |
| DEP_TRANSFER_USD | PARTNER | source_bank_id, bank_reference y routing_number o swift_code; fondos liquidados USD. |

WEB/MOBILE: ERR_CHANNEL_NOT_SUPPORTED. teller puede registrar BRANCH; system registra ATM/PARTNER; client consulta sus cuentas; operations consulta y concilia dentro de su institución. Canal y origen deben estar autorizados por token: no elevar límites declarando BRANCH desde un cliente.

## 3. Política monetaria

| ID | Parámetro | Valor inicial | Frontera |
| --- | --- | --- | --- |
| DOM-007 | Mínimo | 1.00 | Igual admitido. |
| DOM-008 | Máximo BRANCH | 50000.00 | Igual admitido por canal, sujeto a límite acumulado. |
| DOM-009 | Máximo ATM/PARTNER | 5000.00 | Igual admitido. |
| DOM-010 | Límite móvil por cuenta | 20000.00 | Igual admitido; exceso rechazado. |
| DOM-011 | Declaración AML | Desde 10000.00 | Umbral inclusive; exige formulario y fuente. |

Políticas del proyecto, no certificación regulatoria. AML comprueba presencia/formato, no autenticidad ni riesgo. No existe excepción manual a límites.

El máximo BRANCH de 50000.00 es un techo de canal: con cupo global 20000.00, un depósito de 50000.00 se rechaza. Permitirlo exige cambiar la política global y sus escenarios.

Para instante UTC t de admisión: sumar COMPLETED con completed_at > t−24 h y <= t, más todas las reservas activas, aunque sean anteriores a 24 h. Un resultado desconocido nunca libera cupo por antigüedad. La verificación y adquisición de reserva son atómicas por institución/cuenta.

Ejemplo: cupo usado 19000.00 y dos solicitudes concurrentes de 1000.00; exactamente una se admite. Al completar se convierte la reserva en consumo confirmado sin doble conteo. Al rechazar definitivamente se libera. Guardar policy_version y valores efectivos; cambios de política no recalculan reservas anteriores.

## 4. Cuenta y orden de evaluación

DOM-012: Cuentas confirma institución, customer_id, status=ACTIVE, currency=USD o MULTI_CURRENCY, allows_deposits=true, is_frozen=false. MULTI_CURRENCY exige enabled_currencies incluyendo USD. Campo ausente/tipo inválido es fallo contractual; no asumir autorización. Cuentas revalida elegibilidad al abonar.

Orden de creación: autenticación → estructura/headers → autorización de rol/canal/origen e institución del actor → idempotencia → T1 → VALIDATING → compatibilidad tipo/canal → límites por operación → AML → consulta de cuenta y confirmación de institución/elegibilidad → reserva diaria atómica → crédito. Reportar primera regla fallida; errores de estructura pueden agruparse por JSON Pointer. teller/system no necesitan authorized_account_ids: pueden crear para cualquier cuenta de su institución, cuya pertenencia confirma Cuentas después de T1 y antes de reservar. Lecturas usan el ámbito de SPEC-05; la consulta externa nunca amplía permisos.

DOM-016: si Cuentas responde con contrato válido pero institution_id distinto al del actor, o confirma cuenta inexistente, persistir REJECTED con ERR_ACCOUNT_NOT_FOUND, sin reserva ni crédito. La respuesta inicial es 404 con el depósito local y Location, sin revelar institución, propietario ni datos externos. Un replay autorizado repite esa respuesta; GET muestra sólo la representación local segura. Si antes se guardó 202, conservar ese replay y consultar el rechazo actual por GET.

DOM-017: compatibilidad tipo/canal según la tabla de sección 2. Para WEB/MOBILE con rol creador, scope y claim de canal válidos, evaluar ERR_CHANNEL_NOT_SUPPORTED antes de exigir origen específico; no existe variante de origen habilitada para esos canales. Un canal no autorizado por token produce 403 antes de T1. Una combinación incompatible de canales v1 produce ERR_VALIDATION después de T1 si el body es estructuralmente válido.

## 5. Estados y transiciones (DOM-015)

| Estado | Significado | Cupo |
| --- | --- | --- |
| RECEIVED | Petición válida registrada. | Sin reserva. |
| VALIDATING | Evaluación de reglas/cuenta. | Sin reserva. |
| PENDING_CREDIT | Orden durable preparada. | Reserva activa. |
| PENDING_RECONCILIATION | Dependencia impide terminar o resultado incierto. | Reserva activa si ya fue adquirida. |
| COMPLETED | Abono confirmado y persistido. | Consumo por completed_at. |
| REJECTED | Rechazo de negocio o prueba definitiva de ausencia de abono. | Reserva liberada. |

Transiciones únicas:
- RECEIVED → VALIDATING.
- VALIDATING → PENDING_CREDIT, REJECTED o PENDING_RECONCILIATION.
- PENDING_CREDIT → COMPLETED, REJECTED o PENDING_RECONCILIATION.
- PENDING_RECONCILIATION → VALIDATING sólo si nunca se reservó/envió crédito.
- PENDING_RECONCILIATION → PENDING_CREDIT, COMPLETED o REJECTED si tenía reserva; antes de reenviar consultar referencia externa.
- COMPLETED y REJECTED son terminales.

RETRYING es metadato de intento. FAILED_REVERSED se elimina: v1 no tiene contrato de débito compensatorio. Ningún operador puede imponer COMPLETED ni declarar reversión local.

## 6. Idempotencia y origen

DOM-013: unicidad por (institution_id, subject_id, operación, UUIDv4). Hash SHA-256 del cuerpo completo validado y canal; incluir notas, origen y AML, excluir token y correlation_id. Construir objeto con defaults explícitos: notes y aml_declaration ausentes se representan como null sólo en el objeto interno del hash. Canonicalizar con RFC 8785 y amount como cadena decimal. Cambiar orden de propiedades/espacios JSON no cambia hash; cambiar cadenas sí.

Para operación RECONCILE no hay canal: hash del deposit_id de la ruta y cuerpo completo con reason. Para CREATE el objeto canónico tiene claves body y channel. Para RECONCILE tiene claves body y deposit_id. Ambos incluyen operation como clave superior para separar contratos.

Misma clave/hash con resultado guardado: repetir código, body y Location iniciales, incluido 201, 202 o rechazo de negocio. GET devuelve estado actual. Competidor sin resultado inicial: 409 ERR_IDEMPOTENCY_IN_PROGRESS, Retry-After: 1; nunca segunda ejecución. Hash distinto: 409 ERR_IDEMPOTENCY_CONFLICT.

Retener respuesta completa >=24 h desde su persistencia y mientras siga pendiente. Después puede conservarse sólo hash/vínculo: 409 ERR_IDEMPOTENCY_EXPIRED con deposit_id y Location si el recurso sigue disponible y visible. No reciclar clave, incluso después de archivar el depósito; conservar tombstones según SEC-002 y DAT-005. Un fallo sin commit durable no consume clave.

DOM-014: evidencia única por (institución, tipo, emisor, referencia); emisor es branch_id, atm_id o source_bank_id. Nueva clave con evidencia usada: 409 ERR_ORIGIN_ALREADY_USED, sin depósito ni abono nuevos. Sólo divulgar recurso previo si actor tiene acceso.

Para una clave existente del ámbito institution_id/subject_id, comprobar rol/scope/canal actuales y visibilidad del depósito antes de responder sobre hash o fase: origen ya no visible produce 404 conforme a SEC-001. Esta consulta local no autoriza una ejecución nueva; para clave nueva se exige autorización completa de origen antes de T1. Nunca buscar claves de otros sujetos/instituciones.

## 7. Casos de uso

CU-01 Crear: actor autorizado, fondos confirmados; registro durable, validación, reserva y crédito. 201 si completa en presupuesto HTTP o 202 consultable. Rechazo persistido genera REJECTED y Problem Details con deposit_id.
CU-02 Consultar: verificar acceso por institución/cuenta en cada petición; obtener estado actual y motivo seguro.
CU-03 Historial: filtrar autorización antes de contar/paginar; lista vacía si no hay resultados.
CU-04 Comprobante: JSON estable únicamente COMPLETED; no factura fiscal.
CU-05 Conciliar: consultar evidencia externa y recuperar con misma referencia, sin modificar monto ni cuenta.
