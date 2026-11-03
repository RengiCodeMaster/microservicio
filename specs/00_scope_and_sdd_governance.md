# SPEC-00 — Alcance, decisiones y gobierno SDD

Versión: 2.1. Fecha: 2026-10-13. Estado: propuesta implementable para revisión del responsable del proyecto.

## 1. Propósito

Especificar un servicio que registra, valida y coordina depósitos USD, consultables y auditables, sin duplicar abonos incluso ante concurrencia y fallos. Cuentas es propietario del saldo y del asiento contable. El resultado de esta documentación es una definición objetivo; no certifica que el código existente la implemente.

Las cifras monetarias y requisitos AML son políticas académicas propuestas, heredadas del proyecto; no se presentan como obligaciones legales verificadas. Cualquier integración bancaria real requiere que sus responsables definan jurisdicción, política de cumplimiento y acuerdos con Cuentas.

## 2. Alcance v1

Incluye efectivo confirmado por sucursal/ATM, transferencias ya liquidadas enviadas por integrador, creación, consulta, historial, comprobante JSON, idempotencia, reservas de cupo, conciliación, auditoría y ejecución local con PostgreSQL y mock contractual.

Excluye recepción física de billetes, conexión directa a SWIFT/ACH, autenticación del formulario AML, evaluación de riesgo, cambio de moneda, débito de cuenta origen, comisiones, intereses, reversión contable, cancelación, PDF, interfaz gráfica, multicurrency fuera de USD y broker de eventos en v1. WEB/MOBILE son valores reservados; su creación se rechaza hasta definir fuente de fondos.

## 3. Lenguaje y precedencia

DEBE: obligatorio y verificable. NO DEBE: prohibición. PUEDE: opción explícita. Todo requisito numerado es normativo; ejemplos sólo ilustran y deben cumplirlo. Los estados, campos y errores se escriben literalmente.

| Documento | Autoridad |
| --- | --- |
| SPEC-00 | Alcance, supuestos y proceso SDD. |
| SPEC-01 | Reglas y estados del negocio. |
| SPEC-02 | Formatos públicos y externos HTTP. |
| SPEC-03 | Persistencia, transacciones y concurrencia. |
| SPEC-04 | Procesamiento, recuperación e integración. |
| SPEC-05 | Acceso, privacidad y observabilidad. |
| SPEC-06 | Arquitectura y responsabilidades. |
| SPEC-07 | Escenarios de aceptación y trazabilidad. |
| SPEC-08 | Operación, entrega y objetivos medibles. |
| SPEC-09 | Decisiones y riesgos de integración. |

No resolver contradicciones escogiendo silenciosamente un archivo: registrar incidencia, corregir los documentos afectados y actualizar escenarios antes de implementar. El código y agentes no sustituyen estas decisiones.

## 4. Objetivos y vocabulario

Depósito: agregado de negocio identificado por UUID interno, expuesto como dep_usd_<UUIDv4>.
Abono: efecto contable confirmado por Cuentas.
Referencia externa: deposit_id completo, estable en todos los intentos.
Resultado incierto: no puede demostrarse si Cuentas abonó.
Reserva: cupo local retenido antes del envío de crédito.
Institución: ámbito de aislamiento derivado del token, nunca de un campo libre.
Idempotencia: repetición de una operación sin crear un nuevo efecto.
Conciliación: consulta de evidencia externa y recuperación del estado local; no reversión.
Evidencia de origen: comprobante físico o referencia bancaria que identifica los fondos y evita registrarlos otra vez.

## 5. Proceso SDD obligatorio (SDD-001)

1. Revisar dominio, contratos, invariantes y escenarios; documentar una decisión si cambian.
2. Producir OpenAPI 3.1 y migraciones a partir de las specs; revisarlos antes del servicio.
3. Implementar por casos de uso y vincular cambios a requisitos y escenarios.
4. Verificar contratos, dinero, autorización, concurrencia y recuperación sobre PostgreSQL.
5. Publicar evidencia de escenarios aprobados y limitaciones del entorno.

Una historia está lista cuando tiene actor, precondiciones, entradas, salida, fallos, persistencia, autorización y aceptación. Está terminada cuando cumple esos criterios y su documentación no contradice los contratos. No aceptar cobertura porcentual como sustituto de pruebas de invariantes.

## 6. Administración de cambios

Cada cambio registra fecha, motivo, IDs afectados, compatibilidad, migración y pruebas. Cambios de representación monetaria, estados, obligatoriedad de campos y semántica de idempotencia son incompatibles con clientes anteriores: requieren nueva versión o migración coordinada. Esta revisión 2.1 es la nueva base documental, no una promesa de compatibilidad con el código previo.

Nunca renumerar un ID publicado; añadir IDs o marcar obsoletos. Errores y campos nuevos necesitan actualización de SPEC-02, OpenAPI y SPEC-07. Toda política efectiva queda versionada en el depósito. La revisión documental 2.1 mantiene policy_version=usd-v1 y los valores monetarios; su cambio de conservación queda registrado en DEC-14 y requiere ratificación antes de producción.

## 7. Lectura y entregables

Leer 00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09.
Entregables posteriores: OpenAPI validado, migraciones versionadas, mock de Cuentas, servicio API, worker, pruebas contractuales y de concurrencia, contenedores y runbook. Esta fase modifica documentación, no implementación.
