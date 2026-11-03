# SPEC-04 — Procesamiento, resiliencia y conciliación

Versión: 2.1. Presupuesto HTTP y representación: SPEC-02. Transacciones: SPEC-03.

## 1. Flujo normal (RES-001)

1. Validar transporte/identidad y registrar T1.
2. API puede reclamar el job para ejecutar inline; worker no puede reclamarlo simultáneamente.
3. Persistir VALIDATING en T2a, validar compatibilidad/límites/AML, consultar Cuentas y confirmar institución/elegibilidad; adquirir reserva T2 según el orden DOM-012.
4. Enviar crédito con deposit_reference estable; validar respuesta.
5. Confirmar T4 y guardar respuesta T5; responder 201 si COMPLETED, error de negocio si REJECTED o 202 si sigue pendiente.
6. Si vence presupuesto, guardar 202, dejar job recuperable y responder. No cancelar un crédito ya iniciado como si no hubiera ocurrido.

Objetivo: normalmente terminar síncrono, pero procesamiento durable es obligatorio. Desconexión del cliente no elimina trabajo ni reserva. No ejecutar task en memoria como única garantía de continuación.

## 2. Timeouts y retry (RES-002)

| Operación | Connect | Read | Write | Pool | Techo total por intento |
| --- | --- | --- | --- | --- | --- |
| GET cuenta / GET crédito | 0.5 s | 1.5 s | 0.5 s | 0.2 s | 2 s |
| POST crédito | 0.5 s | 2.5 s | 0.5 s | 0.2 s | 3 s |

El techo total es deadline adicional, no suma implícita de parámetros httpx. Request entrante: 8 s incluyendo DB y red; gateway >=10 s. No empezar intento si no quedan su techo +500 ms para persistir respuesta.

GET puede reintentarse una vez inline si cabe; POST tiene sólo un intento inline. Recuperación de POST ocurre por worker, consultando referencia antes de reenviar. Reintentos siempre conservan referencia, monto, cuenta, institución y source_system.

Transitorios: error de conexión, timeout, 429, 500, 502, 503, 504. 429 respeta Retry-After válido limitado a 60 s. 401/403 externos significan credencial/configuración incorrecta y alerta, no rechazo financiero. 409 externo significa conflicto contractual: conciliar y revisión, nunca referencia nueva. Sólo 404/422 del crédito con rechazo definitivo completo INT-002 permiten rechazar/liberar; 400 es fallo contractual. Schema o identidad inválidos llevan directamente a MANUAL_REVIEW, conservando reserva; resultado incierto sin evidencia contractual conserva cupo y se consulta por referencia. Errores de lookup cuenta se mapean únicamente si contrato válido.

## 3. Circuit breaker (RES-003)

Por instancia y dependencia Cuentas, no por cuenta. CLOSED: contar fallos transitorios de intentos; éxito válido reinicia contador. Cinco fallos consecutivos abren 30 s. HALF_OPEN admite máximo dos probes concurrentes de lectura, nunca créditos nuevos como probes; dos éxitos cierran, un fallo abre. Errores de negocio no incrementan fallos. Estado OPEN no hace red; jobs se reprograman.

Cuentas caída no retira la API de readiness: el servicio puede aceptar duraderamente y consultar recursos. Debe devolver 202 para creaciones aceptadas. DB caída sí impide readiness. No afirmar que un breaker local representa estado global del cluster.

## 4. Algoritmo de conciliación (RES-004)

Worker reclama job con lease/generation.
- Si no hubo reserva ni intento de crédito: retomar VALIDATING, volver a consultar cuenta y aplicar política guardada.
- Con reserva o posible envío previo: consultar crédito por referencia autoritativa.
- SUCCESS válido: aplicar COMPLETED y consumir reserva.
- REJECTED definitivo válido: aplicar REJECTED y liberar.
- PROCESSING: esperar, sin reenviar.
- 404: reenviar exactamente el mismo crédito idempotente si no hay breaker abierto; no liberar cupo.
- Timeout, 5xx, conflicto o respuesta incoherente: conservar reserva y reprogramar.

Programación tras fallos: delay = min(300 s, 5 s × 2^min(n−1,6)) + uniforme(0,1 s), n es número de ciclo de conciliación sin resultado terminal, incluido PROCESSING. Máximo 20 ciclos o 24 h desde inicio del ciclo de recuperación, lo primero que ocurra. Al agotarse: job MANUAL_REVIEW, depósito PENDING_RECONCILIATION, conservar reserva si existía, alerta y ninguna nueva red automática. No hay rechazo por agotamiento.

La conciliación manual reanuda el mismo job con contador e inicio de recuperación reiniciados, generation nueva y audit de actor/reason; no cambia datos financieros. Si estaba READY puede adelantarse, si LEASED no se interrumpe y se devuelve conflicto. Ante error contractual/conflicto de referencia, pasar directamente a MANUAL_REVIEW, sin retry ciego. Operador investiga con Cuentas y luego solicita otra consulta; no edita estado ni ejecuta un nuevo abono. La solicitud manual pasa RUNNING al reclamar, DONE al terminar el depósito o MANUAL_REVIEW si agota recuperación; finished_at se guarda en ambos resultados finales de la solicitud.

El paso inmediato por error contractual/conflicto también finaliza la solicitud manual RUNNING como MANUAL_REVIEW, con finished_at de DB y last_error_code seguro en el job. Depósito PENDING_RECONCILIATION, job MANUAL_REVIEW, cierre de solicitud y auditoría de transición cuando corresponda se confirman juntos bajo generation vigente. Se conserva la reserva y se emite alerta después del commit; ninguna nueva llamada automática se ejecuta hasta otra solicitud manual. Cada reactivación crea una nueva reconciliation_request y conserva el resultado final de la anterior.

Job RECEIVED/VALIDATING abandonado se recupera dentro de 60 s. Job con lease expirado después de enviar crédito debe consultar referencia. Caída entre éxito externo y commit local es el escenario principal que este algoritmo debe resolver.

## 5. Backpressure y apagado (RES-005)

Un worker ejecuta máximo 10 llamadas externas simultáneas; API máximo 20; pools limitados y bounded queue. Cola durable máxima propuesta 10000 jobs no terminales por despliegue: superar umbral impide T1 nuevo con 503 ERR_ACCOUNTS_SERVICE_UNAVAILABLE, sin afectar consultas/replays. Medición de umbral es control operativo aproximado, no invariante contable.

SIGTERM: marcar instancia no ready, dejar de reclamar, esperar hasta 30 s, persistir resultados disponibles; trabajos restantes se recuperan por leases. No liberar reservas al apagar. No sostener locks SQL durante espera externa.

## 6. Mock e integración (RES-006)

Mock usa almacenamiento durable de referencias para demostrar deduplicación después de reinicio. Escenarios deterministas: éxito, rechazo, demora antes de abono, abono seguido de timeout, 5xx antes/después de abono, PROCESSING, 404, respuesta incoherente y credencial inválida. Fallos configurables sólo en entorno local/prueba, sin endpoint de inyección en producción.

Integración se acepta sólo cuando Cuentas demuestra por contrato y pruebas unicidad de referencia, lookup autoritativo y rechazo irreversible por referencia. Sin ello, una demo local no prueba seguridad contable distribuida.
