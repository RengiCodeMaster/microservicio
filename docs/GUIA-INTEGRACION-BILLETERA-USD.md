# Guía Rápida de Integración: Billetera Digital USD ➡️ Microservicio de Depósitos USD

Esta guía contiene la información exacta y ejemplos listos para que el equipo de **Billetera Digital USD** conecte sus recargas/depósitos con el **Microservicio de Depósitos en Dólares (`usd-deposit-service`)**.

---

## 1. Endpoint Principal

- **URL Base:** http://a79e1592417ac404992dde1843665a69-846392940.us-east-1.elb.amazonaws.com
- **Swagger Docs:** http://a79e1592417ac404992dde1843665a69-846392940.us-east-1.elb.amazonaws.com/docs

- **Método:** `POST`
- **Ruta:** `/api/v1/deposits/usd`
- **Content-Type:** `application/json`

---

## 2. Cabeceras HTTP

| Cabecera                                                    | Requerido     | Descripción                                                                            | Ejemplo                                  |
| :---------------------------------------------------------- | :------------ | :-------------------------------------------------------------------------------------- | :--------------------------------------- |
| **`Idempotency-Key`** *(o `X-Idempotency-Key`)* | **Sí** | UUIDv4 único por transacción. Previene duplicidad de cobros si hay reintentos de red. | `550e8400-e29b-41d4-a716-446655440000` |
| **`X-Channel`**                                     | Opcional      | Canal que origina la operación. Usar `PARTNER` o `WEB`. (Default: `BRANCH`)      | `PARTNER`                              |
| **`X-Correlation-Id`**                              | Opcional      | ID de trazabilidad distribuida para logs. Si se omite, se genera uno nuevo.             | `7cd14140-2c6d-4fac-b522-76e66a51e2aa` |

---

## 3. Cuerpo de la Petición (Payload)

### Mapeo desde Billetera USD:

- `cuenta_destino_id` ➡️ `target_account_id`
- `monto` ➡️ `amount` (string o número decimal con 2 decimales, ej: `250.00`)
- `moneda` ➡️ `currency` (`"USD"`)
- `metodo_origen` ➡️ `deposit_type` (`"DEP_TRANSFER_USD"` o `"DEP_CASH_USD"`)
- `cliente_id` / `nombre` ➡️ `origin_details`

```json
{
  "target_account_id": "ACC-USD-88992211",
  "amount": 250.00,
  "currency": "USD",
  "deposit_type": "DEP_TRANSFER_USD",
  "origin_details": {
    "depositor_id_type": "DNI",
    "depositor_id_number": "74883321",
    "depositor_full_name": "Maria Perez"
  }
}
```

---

## 4. Respuestas del Servicio

### ✅ Éxito (HTTP 201 Created)

Devuelve el detalle del depósito confirmado y el código contable de transacción:

```json
{
  "deposit_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "COMPLETED",
  "target_account_id": "ACC-USD-88992211",
  "amount": "250.00",
  "currency": "USD",
  "fee_applied": "0.00",
  "net_credited_amount": "250.00",
  "account_service_tx_id": "ACC-TX-5544",
  "created_at": "2026-11-04T04:30:00Z",
  "completed_at": "2026-11-04T04:30:01Z",
  "receipt_url": "/api/v1/deposits/usd/3fa85f64-5717-4562-b3fc-2c963f66afa6/receipt",
  "error_reason": null
}
```

### 🔁 Reintento Seguro / Idempotencia (HTTP 201 con datos previos)

Si la Billetera reenvía la misma `Idempotency-Key` con el mismo payload, el servicio responde inmediatamente con el resultado anterior sin volver a abonar dinero.

### ⚠️ Errores Financieros y de Cumplimiento (Formato RFC 7807)

- **Conflicto de Idempotencia (HTTP 409):** Misma `Idempotency-Key` enviada con un payload o monto diferente.
- **Cuenta no existe o no admite USD (HTTP 404 / 422):** Si la cuenta no está activa o es en soles/euros.
- **Límite diario superado (HTTP 422):** Si el monto acumulado del cliente en el día excede \$20,000.00 USD.
- **Declaración AML requerida (HTTP 422):** Para depósitos unitarios iguales o mayores a \$10,000.00 USD, se requiere adjuntar el objeto `aml_declaration`.

Ejemplo de respuesta de error:

```json
{
  "type": "https://banco.com/errors/ERR_ACCOUNT_FROZEN",
  "title": "Cuenta congelada o inactiva",
  "status": 422,
  "detail": "La cuenta destino se encuentra bloqueada para recibir abonos.",
  "code": "ERR_ACCOUNT_FROZEN",
  "correlation_id": "7cd14140-2c6d-4fac-b522-76e66a51e2aa"
}
```

---

## 5. Ejemplo de Consumo con `curl`

```bash
curl -X POST "http://localhost:8000/api/v1/deposits/usd" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000" \
  -H "X-Channel: PARTNER" \
  -H "X-Correlation-Id: 7cd14140-2c6d-4fac-b522-76e66a51e2aa" \
  -d '{
    "target_account_id": "ACC-USD-88992211",
    "amount": 250.00,
    "currency": "USD",
    "deposit_type": "DEP_TRANSFER_USD",
    "origin_details": {
      "depositor_id_type": "DNI",
      "depositor_id_number": "74883321",
      "depositor_full_name": "Maria Perez"
    }
  }'
```
