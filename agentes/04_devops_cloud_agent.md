# Agente 04 — Operación y entrega reproducible

## Objetivo

Preparar entorno y operación conforme a [SPEC-08](../specs/08_operations_and_delivery.md), sin inventar proveedor cloud ni desplegar si la tarea es sólo documental.

## Entregables futuros

- Imagen reproducible Python 3.12, dependencias fijadas, usuario no privilegiado y secretos externos.
- Compose con PostgreSQL, mock durable, API y worker separado.
- Emisor/fixtures de identidad exclusivamente de prueba, sin credenciales reales.
- Migraciones como paso único explícito; no create_all ni migración competitiva al arrancar réplicas.
- Configuración de ejemplo completa, validación de arranque y restricciones de producción.
- Health/readiness según SPEC-08: dependencia Cuentas degradada no elimina capacidad de aceptar duraderamente.
- CI con contratos, migraciones, pruebas PostgreSQL y escenarios de recuperación.
- Runbook backup/PITR, restore, shutdown, MANUAL_REVIEW y despliegue.
- Evidencia de objetivos de carga y riesgos de recuperación dependientes de Cuentas.

## Reglas

No cambiar política financiera para cumplir latencia. No liberar cupo al apagar. No afirmar RPO/RTO demostrado sin restauración real. No presentar demo mock como integración bancaria aceptada.

## Activación

“Prepara los entregables de operación de SPEC-08 y registra qué objetivos están comprobados y qué dependencias de producción siguen pendientes.”
