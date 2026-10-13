# SPEC-02: Contratos de API REST (OpenAPI / RFC 7807)

## 1. Headers Estándar Obligatorios

| Header | Tipo | Requerido | Descripción |
| :--- | :--- | :--- | :--- |
| `X-Correlation-ID` | UUIDv4 | Sí | Identificador único de trazabilidad distribuida de la petición. |
| `X-Idempotency-Key`| UUIDv4 | Sí en POST | Clave única de idempotencia por operación. |
| `X-Channel` | String | Sí | Canal de origen: `BRANCH`, `ATM`, `WEB`, `MOBILE`, `PARTNER`. |
| `Authorization` | String | Sí | Token Bearer JWT con roles de acceso (`teller`, `client`, `system`). |

---

## 2. Endpoints del Microservicio

### 2.1. Crear Depósito en Dólares
- **Método**: `POST`
- **Ruta**: `/api/v1/deposits/usd`
- **Descripción**: Inicia, valida y procesa el depósito en dólares hacia la cuenta destino.

#### Request Body:
```json
{
  "target_account_id": "ACC-USD-88992211",
  "amount": 1500.50,
  "currency": "USD",
  "deposit_type": "DEP_CASH_USD",
  "origin_details": {
    "depositor_id_type": "DNI",
    "depositor_id_number": "74883321",
    "depositor_full_name": "Carlos Gomez",
    "branch_id": "BR-MIRAFLORES-01",
    "teller_id": "USER-TL-509"
  },
  "aml_declaration": {
    "aml_form_id": "AML-2026-00492",
    "funds_source": "SALARY"
  },
  "notes": "Depósito de ahorros en efectivo"
}
```

#### Response Exitosa (`201 Created`):
```json
{
  "deposit_id": "dep_usd_7f9c8d6e-9311-4702-861a-0e9b97b0a884",
  "status": "COMPLETED",
  "target_account_id": "ACC-USD-88992211",
  "amount": 1500.50,
  "currency": "USD",
  "fee_applied": 0.00,
  "net_credited_amount": 1500.50,
  "account_service_tx_id": "ACC-TX-55441199",
  "created_at": "2026-10-06T14:58:00.000Z",
  "completed_at": "2026-10-06T14:58:01.120Z",
  "receipt_url": "/api/v1/deposits/usd/dep_usd_7f9c8d6e-9311-4702-861a-0e9b97b0a884/receipt"
}
```

---

### 2.2. Consultar Depósito por ID
- **Método**: `GET`
- **Ruta**: `/api/v1/deposits/usd/{deposit_id}`

#### Response (`200 OK`):
```json
{
  "deposit_id": "dep_usd_7f9c8d6e-9311-4702-861a-0e9b97b0a884",
  "status": "COMPLETED",
  "target_account_id": "ACC-USD-88992211",
  "amount": 1500.50,
  "currency": "USD",
  "deposit_type": "DEP_CASH_USD",
  "account_service_tx_id": "ACC-TX-55441199",
  "correlation_id": "c8a16dbb-7a32-4d2b-a4ff-3bcf91280332",
  "created_at": "2026-10-06T14:58:00.000Z",
  "updated_at": "2026-10-06T14:58:01.120Z"
}
```

---

### 2.3. Listar Historial de Depósitos
- **Método**: `GET`
- **Ruta**: `/api/v1/deposits/usd?target_account_id=ACC-USD-88992211&status=COMPLETED&limit=20&offset=0`

#### Response (`200 OK`):
```json
{
  "items": [
    {
      "deposit_id": "dep_usd_7f9c8d6e-9311-4702-861a-0e9b97b0a884",
      "amount": 1500.50,
      "currency": "USD",
      "status": "COMPLETED",
      "created_at": "2026-10-06T14:58:00.000Z"
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

### 2.4. Endpoint de Conciliación Manual (Admin / Reintento)
- **Método**: `POST`
- **Ruta**: `/api/v1/deposits/usd/{deposit_id}/reconcile`
- **Descripción**: Permite a un operador administrativo o tarea batch reintentar o sincronizar el estado de depósitos que quedaron en `PENDING_CREDIT` por fallas de conectividad hacia el Microservicio de Cuentas.

---

## 3. Especificación de Errores Estándar (RFC 7807 Problem Details)

Todos los errores retornan `Content-Type: application/problem+json` con este esquema:

```json
{
  "type": "https://api.banco.com/errors/ERR_ACCOUNT_CURRENCY_MISMATCH",
  "title": "Moneda de cuenta incompatible",
  "status": 422,
  "detail": "La cuenta ACC-EUR-100293 está denominada en EUR y no admite depósitos directos en USD.",
  "instance": "/api/v1/deposits/usd",
  "code": "ERR_ACCOUNT_CURRENCY_MISMATCH",
  "correlation_id": "c8a16dbb-7a32-4d2b-a4ff-3bcf91280332",
  "timestamp": "2026-10-06T14:58:10.450Z"
}
```

### Catálogo de Códigos de Error de Negocio:
| Código | HTTP Status | Causa |
| :--- | :--- | :--- |
| `IDEMPOTENCY_CONFLICT` | 409 | Se reutilizó un `Idempotency-Key` con payload diferente. |
| `ERR_ACCOUNT_NOT_FOUND` | 404 | El Microservicio de Cuentas respondió que la cuenta no existe. |
| `ERR_ACCOUNT_FROZEN` | 422 | La cuenta receptora se encuentra bloqueada judicial o administrativamente. |
| `ERR_ACCOUNT_CURRENCY_MISMATCH` | 422 | La cuenta receptora no admite dólares (USD). |
| `ERR_AML_DECLARATION_REQUIRED` | 422 | El monto es >= 10,000 USD y no se envió el formulario AML obligatorio. |
| `ERR_DAILY_LIMIT_EXCEEDED` | 422 | Se supera el límite diario de depósitos en USD para la cuenta. |
| `ERR_ACCOUNTS_SERVICE_UNAVAILABLE` | 503 | El Microservicio de Cuentas no responde y el Circuit Breaker está abierto. |

---

## 4. Contrato Externo: Comunicación con el Microservicio de Cuentas

### `GET {ACCOUNTS_SERVICE_URL}/api/v1/accounts/{account_id}`
- **Timeout**: 3000 ms
- **Respuesta esperada**:
```json
{
  "account_id": "ACC-USD-88992211",
  "customer_id": "CUST-9922",
  "status": "ACTIVE",
  "currency": "USD",
  "allows_deposits": true,
  "is_frozen": false
}
```

### `POST {ACCOUNTS_SERVICE_URL}/api/v1/accounts/{account_id}/credits`
- **Timeout**: 5000 ms
- **Payload**:
```json
{
  "deposit_reference": "dep_usd_7f9c8d6e-9311-4702-861a-0e9b97b0a884",
  "amount": 1500.50,
  "currency": "USD",
  "channel": "BRANCH",
  "concept": "Depósito en dólares ventanilla"
}
```
- **Respuesta esperada (`200 OK` o `201 Created`)**:
```json
{
  "transaction_id": "ACC-TX-55441199",
  "account_id": "ACC-USD-88992211",
  "new_balance": 4500.50,
  "credited_amount": 1500.50,
  "currency": "USD",
  "status": "SUCCESS"
}
```
