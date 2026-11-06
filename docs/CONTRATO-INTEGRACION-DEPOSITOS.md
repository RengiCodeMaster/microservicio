# Contrato de Integración — Microservicio de Depósitos en Dólares (USD)

Este documento contiene la información técnica, URLs, encabezados y especificaciones OpenAPI que los microservicios compañeros (Cuentas, Retiros, Billeteras, Canales) necesitan para consumir este microservicio.

---

## 1. Conectividad y Acceso Público

| Parámetro | Detalle |
| :--- | :--- |
| **URL Base (Internet / HTTP)** | `http://a79e1592417ac404992dde1843665a69-846392940.us-east-1.elb.amazonaws.com` |
| **Salud (Liveness)** | `GET http://a79e1592417ac404992dde1843665a69-846392940.us-east-1.elb.amazonaws.com/health/live` |
| **Salud (Readiness)** | `GET http://a79e1592417ac404992dde1843665a69-846392940.us-east-1.elb.amazonaws.com/health/ready` |
| **Documentación Swagger / OpenAPI** | `http://a79e1592417ac404992dde1843665a69-846392940.us-east-1.elb.amazonaws.com/docs` |
| **Especificación OpenAPI (JSON)** | `http://a79e1592417ac404992dde1843665a69-846392940.us-east-1.elb.amazonaws.com/openapi.json` |
| **Región AWS** | `us-east-1` (N. Virginia) |
| **Clúster EKS** | `medio-curso-eks` (Namespace: `deposit`) |
| **Moneda admitida** | Exclusivamente **`USD`** (Dólares Americanos) |
| **Formato monetario** | String con dos decimales, ej: `"1500.50"` (evita errores de redondeo IEEE 754) |

---

## 2. Cabeceras HTTP Requeridas

Todas las peticiones a la API deben incluir:

```http
Content-Type: application/json
X-Idempotency-Key: <UUIDv4>
X-Channel: <BRANCH | ATM | WEB | MOBILE | PARTNER>
X-Correlation-ID: <UUIDv4-opcional>
```

- **`X-Idempotency-Key` (Obligatorio en POST)**: Clave única UUIDv4 generada por el cliente. Si la red falla y reenvías la solicitud con la misma clave, el servicio devolverá la respuesta almacenada sin duplicar el abono de dinero.
- **`X-Channel` (Opcional, default: `BRANCH`)**: Canal que origina la operación (`BRANCH`, `ATM`, `WEB`, `MOBILE`, `PARTNER`).
- **`X-Correlation-ID` (Opcional)**: ID de trazabilidad distribuida para rastrear la solicitud a lo largo de todos los microservicios. Si no se envía, el microservicio generará uno automáticamente.

---

## 3. Endpoints Principales

### 3.1. Registrar y Procesar un Depósito en USD
- **Método**: `POST`
- **Ruta**: `/api/v1/deposits/usd`

#### Ejemplo de Petición (Depósito en Efectivo en Sucursal):
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
    "branch_id": "BR-01",
    "teller_id": "USER-TL-509"
  }
}
```

#### Ejemplo de Petición (Depósito por Transferencia):
```json
{
  "target_account_id": "ACC-USD-88992211",
  "amount": "3000.00",
  "currency": "USD",
  "deposit_type": "DEP_TRANSFER_USD",
  "origin_details": {
    "source_bank_id": "BANK-EXT-01",
    "bank_reference": "TX-EXT-998877",
    "swift_code": "BNKUS33A"
  }
}
```

> **Nota AML (Lavado de Activos)**: Si el monto es $\ge \$10,000.00\text{ USD}$, se exige el objeto `"aml_declaration"`:
> ```json
> "aml_declaration": {
>   "aml_form_id": "AML-2026-0012",
>   "funds_source": "SALARY"
> }
> ```

#### Respuesta Exitosa (`201 Created`):
```json
{
  "deposit_id": "dep_usd_7f9c8d6e-9311-4702-861a-0e9b97b0a884",
  "status": "COMPLETED",
  "target_account_id": "ACC-USD-88992211",
  "amount": "1500.50",
  "currency": "USD",
  "fee_applied": "0.00",
  "net_credited_amount": "1500.50",
  "account_service_tx_id": "ACC-TX-55441199",
  "created_at": "2026-11-03T20:20:00Z",
  "completed_at": "2026-11-03T20:20:01Z",
  "receipt_url": "/api/v1/deposits/usd/dep_usd_7f9c8d6e-9311-4702-861a-0e9b97b0a884/receipt"
}
```

---

### 3.2. Consultar Estado de un Depósito
- **Método**: `GET`
- **Ruta**: `/api/v1/deposits/usd/{deposit_id}`
- **Respuesta (`200 OK`)**: Mismo esquema del objeto `DepositResponseDTO`.

---

### 3.3. Obtener Comprobante Digital
- **Método**: `GET`
- **Ruta**: `/api/v1/deposits/usd/{deposit_id}/receipt`
- **Respuesta (`200 OK`)**:
```json
{
  "institution": "BANCO FINANCIERO DE LA NUBE",
  "voucher_title": "CONSTANCIA DE DEPÓSITO EN MONEDA EXTRANJERA (USD)",
  "deposit_id": "dep_usd_7f9c8d6e-9311-4702-861a-0e9b97b0a884",
  "account_id": "ACC-USD-88992211",
  "amount": "1500.50 USD",
  "status": "COMPLETED",
  "operation_code": "ACC-TX-55441199",
  "timestamp": "2026-11-03T20:20:01Z"
}
```

---

### 3.4. Listar Historial de Depósitos
- **Método**: `GET`
- **Ruta**: `/api/v1/deposits/usd?target_account_id=ACC-USD-88992211&limit=20&offset=0`
- **Respuesta (`200 OK`)**:
```json
{
  "items": [
    {
      "deposit_id": "dep_usd_7f9c8d6e-9311-4702-861a-0e9b97b0a884",
      "amount": "1500.50",
      "currency": "USD",
      "status": "COMPLETED",
      "created_at": "2026-11-03T20:20:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 20,
    "offset": 0
  }
}
```

---

## 4. Respuestas de Error (RFC 7807 / RFC 9457)

En caso de error, el servicio responde con `Content-Type: application/problem+json`:

```json
{
  "type": "https://banco.com/errors/ERR_DAILY_LIMIT_EXCEEDED",
  "title": "Límite diario excedido",
  "status": 422,
  "detail": "El depósito supera el límite diario permitido de 20000.00 USD.",
  "instance": "/api/v1/deposits/usd",
  "code": "ERR_DAILY_LIMIT_EXCEEDED",
  "correlation_id": "c8a16dbb-7a32-4d2b-a4ff-3bcf91280332"
}
```

### Catálogo de Códigos de Error:
- `ERR_DAILY_LIMIT_EXCEEDED` (422): Supera el límite diario de $20,000 USD.
- `ERR_AML_DECLARATION_REQUIRED` (422): Montos $\ge \$10,000\text{ USD}$ sin declaración AML.
- `ERR_ACCOUNT_CURRENCY_MISMATCH` (422): La cuenta destino no es USD (ej. es PEN o EUR).
- `ERR_ACCOUNT_FROZEN` (422): La cuenta está bloqueada o congelada.
- `ERR_ACCOUNT_NOT_FOUND` (404): La cuenta no existe en el microservicio de Cuentas.
- `ERR_ACCOUNTS_SERVICE_UNAVAILABLE` (503): El microservicio de Cuentas está caído o inaccesible.
- `IDEMPOTENCY_CONFLICT` (409): Se reutilizó la misma `X-Idempotency-Key` con un monto o cuenta diferente.

---

## 5. Integración con el Microservicio de Cuentas (Saliente)

Nuestro microservicio invoca al servicio de Cuentas en dos momentos:
1. `GET {ACCOUNTS_SERVICE_URL}/api/v1/accounts/{account_id}` (Verificación de existencia, estado y moneda).
2. `POST {ACCOUNTS_SERVICE_URL}/api/v1/accounts/{account_id}/credits` (Abono de saldo).

Para apuntar a la infraestructura del compañero de Cuentas, simplemente se actualiza el valor `ACCOUNTS_SERVICE_URL` en nuestro `ConfigMap`.

