# SPEC-09 — Decisiones y riesgos pendientes de integración

Versión: 2.1. Las decisiones siguientes constituyen la base documental propuesta. Pendientes externos no impiden construir demo con mock, pero sí afirmar disponibilidad productiva.

## 1. Registro de decisiones

| ID | Decisión / motivo | Consecuencia |
| --- | --- | --- |
| DEC-01 | Dinero string decimal en JSON, Decimal interno y NUMERIC SQL. | Evita ambigüedad binaria; incompatible con contrato anterior numérico. |
| DEC-02 | Resultado incierto permanece PENDING_RECONCILIATION; eliminar FAILED_REVERSED. | No se afirma reversión inexistente; reserva puede necesitar operador. |
| DEC-03 | Cuentas deduplica por referencia y permite lookup autoritativo. | Dependencia obligatoria para seguridad distribuida. |
| DEC-04 | Cupo incorpora reservas y se serializa por cuenta. | Depósitos concurrentes no superan política. |
| DEC-05 | PostgreSQL jobs en v1, broker fuera de alcance. | Continuación durable sin infraestructura adicional; outbox futuro. |
| DEC-06 | Demo Docker Compose, proveedor cloud posterior. | No hay promesa AWS/GCP ni infraestructura productiva definida. |
| DEC-07 | Límites/AML/retención son políticas académicas propuestas. | Responsable de negocio/compliance valida antes de operar fondos reales. |
| DEC-08 | Restauración requiere exportación autoritativa de créditos de Cuentas. | Backup local solo no reconstruye ventana perdida. |
| DEC-09 | Sólo efectivo BRANCH/ATM y transferencia PARTNER liquidada. | WEB/MOBILE reservados hasta definir fuente de fondos. |
| DEC-10 | Replay conserva respuesta inicial; GET informa avance. | 202 puede repetirse aun si ya completó. |
| DEC-11 | Clave no se reutiliza tras ventana de replay. | Conservar hash/vínculo o archivo deduplicable. |
| DEC-12 | completed_at local determina consumo 24 h; credited_at conserva fecha externa. | Confirmaciones tardías consumen cupo durante 24 h posteriores a confirmación local. |
| DEC-13 | Rechazo definitivo externo tipado y vinculado al crédito, con catálogo cerrado INT-002. | HTTP por sí solo no libera cupo; schema/código desconocido requiere revisión manual. |
| DEC-14 | Retención técnica mínima de 365 días seguida de archivo lógico sin purga automática v1. | Deduplicación conserva claves/orígenes/referencias sin vencimiento automático; requiere ratificación EXT-04. |
| DEC-15 | Autorización de creador previa a T1 y pertenencia de cuenta confirmada después, sin claims de cuentas para teller/system. | Rechazo seguro durable; replay revalida permisos actuales y visibilidad local. |

## 2. Dependencias y preguntas externas

| ID | Responsable / dato necesario | Resolución para demo | Bloqueo de producción |
| --- | --- | --- | --- |
| EXT-01 | Equipo Cuentas: idempotencia durable, lookup, rechazo por referencia, exportación. | Mock conforme INT-001. | Sí, sin pruebas contractuales y recuperación. |
| EXT-02 | Identidad: issuer/JWKS, claims, roles, credenciales de servicio. | Emisor y claves ficticias locales. | Sí, sin proveedor confiable. |
| EXT-03 | Canales: evidencia única, recepción/liquidación confirmada y orígenes. | Fixtures deterministas. | Sí, sin garantía de origen de fondos. |
| EXT-04 | Negocio: ratificar límites, ausencia de comisiones, AML y tiempos de retención. | Valores propuestos SPEC-01/05. | Sí, requiere política institucional. |
| EXT-05 | Infraestructura: red, secretos, logs, gateway/rate limit, backup/WAL y SLO. | Compose local, pruebas controladas. | Sí, requiere entorno y runbook verificado. |
| EXT-06 | Cumplimiento: jurisdicción y validación de declaraciones/formularios. | Sólo validación de forma, explícita. | Sí, si se pretende cumplimiento real. |

No confundir elección de demo con respuesta confirmada por un tercero. El implementador registra evidencia de cada contrato y contacto responsable en entrega, sin inventar un acuerdo existente.

## 3. Riesgos y tratamiento

- Cuentas abona y respuesta se pierde: referencia estable, lookup y reserva activa.
- Dos depósitos compiten por cupo: fila de bloqueo por cuenta, cálculo/reserva atómicos.
- Nueva clave repite mismos fondos: unicidad de evidencia de origen.
- Worker muere: job durable, lease y generation; reconsulta antes del crédito.
- Cuentas devuelve datos incoherentes: MANUAL_REVIEW, no éxito fabricado.
- Restauración pierde metadatos de abonos: detener admisión y reconstruir desde evidencia externa.
- Reserva incierta reduce disponibilidad: alerta/operador, jamás liberar automáticamente.
- Código previo usa reglas antiguas: tratarlo como implementación a migrar, no fuente de verdad.
- Retención elimina deduplicación: conservar tombstones/referencias antes de purgar datos personales.

## 4. Cambios frente a versión anterior

Normalización ATM, catálogo ERR_ uniforme, dinero string, correlation opcional generado, auth definida por recurso, net_credited_amount nullable, comprobante especificado, conciliación contractual, reservas concurrentes, seis estados coherentes, deadlines únicos y jobs durables. Se conserva el techo BRANCH de 50000.00 y se explica subordinación al cupo 20000.00. Readiness refleja DB/esquema y permite Cuentas degradada.

## 5. Plantilla para decisiones futuras

ID y fecha; problema; opciones; decisión; motivos; requisitos/AC afectados; cambio de contrato; migración; riesgos; evidencia de validación; responsable. Cambiar primero specs y aceptación; después implementar.

## 6. Registro de revisión 2.1 — 2026-10-13

Motivo: resolver contradicciones detectadas en autorización, rechazos externos, persistencia de estados, anonimización y cierre de conciliación. Responsable de esta propuesta: revisión documental del proyecto; ratificación institucional pendiente según EXT-01/04.

Requisitos afectados: DOM-012/013/014/015; nuevos DOM-016/017, INT-002 y DAT-005; INT-001, DAT-001/003, RES-001/002/004, SEC-001/002. Corregidos AC-03/04/29/31; añadidos AC-45..52 sin renumerar escenarios existentes.

Compatibilidad: se mantienen rutas, dinero y límites públicos; se precisa orden de errores y replay. El contrato externo agrega identidad de SUCCESS y objetos completos de rechazo/PROCESSING/404, por lo que el mock y Cuentas deben adaptarse antes de integración. El esquema añade marcadores de anonimización y permite reason NULL sólo después de anonimizar; migraciones posteriores deben validar datos antes de activar constraints. No se migra implementación en esta fase.

Verificación requerida: derivar OpenAPI de los contratos revisados, actualizar fixtures/migraciones y ejecutar AC-45..52 junto con los escenarios modificados. La inspección documental no representa PASS de aceptación. Riesgos pendientes: acuerdo externo sobre rechazo irreversible, protección de identidad y conservación productiva; conservar referencias indefinidamente en demo no equivale a política institucional aprobada.
