# SPEC-04: Resiliencia en la Nube e Integración Entre Servicios

## 1. Patrones de Resiliencia Cloud-Native

```mermaid
graph TD
    Client["Cliente / Canal (Web/ATM)"] -->|POST /api/v1/deposits/usd| MS["Microservicio Depósitos USD"]
    MS --> DB[(PostgreSQL + Outbox)]
    MS -->|HTTP Client con Resiliencia| CB{"Circuit Breaker"}
    CB -->|CLOSED: Flujo Normal| AccountsMS["Microservicio Cuentas (Remoto)"]
    CB -->|OPEN: Falla Rápida (503)| Fallback["Manejador de Fallback / Outbox"]
    CB -->|TIMEOUT / 5xx| Retry["Exponential Backoff + Jitter (x3)"]
    Retry --> AccountsMS
```

### 1.1. Circuit Breaker
- **Propósito**: Evitar saturación en cascada si el Microservicio de Cuentas se degrada o cae.
- **Configuración**:
  - `failure_threshold`: 5 fallas consecutivas (5xx o ConnectTimeout).
  - `recovery_timeout`: 30 segundos (transición a estado `HALF-OPEN`).
  - `half_open_success_threshold`: 2 peticiones exitosas para volver a `CLOSED`.
  - **Comportamiento en OPEN**: Retorna de inmediato HTTP `503 Service Unavailable` con código `ERR_ACCOUNTS_SERVICE_UNAVAILABLE` sin saturar la red.

### 1.2. Política de Reintentos (Exponential Backoff + Jitter)
- **Criterio de reintento**: Únicamente en fallos transitorios (`ConnectTimeout`, `ReadTimeout`, `502`, `503`, `504`).
- **NUNCA reintentar**: Errores `4xx` (`400 Bad Request`, `404 Not Found`, `422 Unprocessable Entity`), pues son deterministas.
- **Fórmula de backoff**:
  $$\text{Delay} = \min(\text{max\_delay}, \text{base\_delay} \times 2^{\text{attempt}}) + \text{jitter}$$
  - `base_delay`: 500 ms
  - `max_delay`: 4000 ms
  - `max_retries`: 3

### 1.3. Timeouts Estrictos
- `connect_timeout`: 2.0 segundos.
- `read_timeout`: 4.0 segundos.
- `write_timeout`: 2.0 segundos.

---

## 2. Health Checks para Entornos Cloud (Kubernetes / ECS / Cloud Run)

### 2.1. Liveness Probe (`GET /health/live`)
- **Propósito**: Indicar si el proceso de FastAPI está vivo y no bloqueado en un bucle o deadlock.
- **Respuesta**: HTTP `200 OK` `{"status": "UP"}`.

### 2.2. Readiness Probe (`GET /health/ready`)
- **Propósito**: Indicar si el microservicio está listo para recibir tráfico de balanceador.
- **Validaciones**:
  1. Conexión activa a PostgreSQL (`SELECT 1;`).
  2. Estado del Circuit Breaker hacia el Microservicio de Cuentas.
- **Respuesta (`200 OK` si todo OK, `503 Service Unavailable` si la BD no responde)**:
```json
{
  "status": "READY",
  "dependencies": {
    "database": "UP",
    "accounts_service_circuit_breaker": "CLOSED"
  },
  "timestamp": "2026-10-06T15:00:00Z"
}
```

---

## 3. Configuración 12-Factor App (Variables de Entorno)

| Variable | Tipo | Default | Descripción |
| :--- | :--- | :--- | :--- |
| `ENV` | String | `development` | Entorno: `development`, `testing`, `production`. |
| `PORT` | Integer | `8000` | Puerto HTTP del servicio. |
| `DATABASE_URL` | String | `postgresql+asyncpg://...` | Cadena de conexión async a PostgreSQL. |
| `ACCOUNTS_SERVICE_URL` | String | `http://accounts-service:8080` | URL base del Microservicio de Cuentas. |
| `ACCOUNTS_SERVICE_TIMEOUT_SEC` | Float | `5.0` | Timeout total por llamada. |
| `DAILY_LIMIT_USD` | Float | `20000.00` | Límite máximo de depósito en 24h por cuenta. |
| `AML_THRESHOLD_USD` | Float | `10000.00` | Umbral para exigir declaración jurada AML. |
| `LOG_LEVEL` | String | `INFO` | Nivel de logs: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
