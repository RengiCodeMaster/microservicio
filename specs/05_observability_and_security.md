# SPEC-05: Observabilidad, Seguridad y Auditoría

## 1. Logs Estructurados en JSON

Para ser ingeridos por CloudWatch, Datadog o Grafana Loki, cada línea de log debe emitirse en formato JSON estructurado conteniendo obligatoriamente los metadatos de trazabilidad:

```json
{
  "timestamp": "2026-10-06T15:00:01.120Z",
  "level": "INFO",
  "logger": "usd_deposit_service.service",
  "message": "Depósito procesado y acreditado con éxito",
  "correlation_id": "c8a16dbb-7a32-4d2b-a4ff-3bcf91280332",
  "deposit_id": "dep_usd_7f9c8d6e-9311-4702-861a-0e9b97b0a884",
  "target_account_id_masked": "ACC-USD-****2211",
  "amount": 1500.50,
  "currency": "USD",
  "channel": "BRANCH",
  "elapsed_ms": 128.4
}
```

---

## 2. Métricas Clave de Negocio y Sistema (Prometheus)

El microservicio expone `/metrics` con las siguientes métricas instrumentadas:

| Nombre de la Métrica | Tipo | Labels | Propósito |
| :--- | :--- | :--- | :--- |
| `usd_deposits_requests_total` | Counter | `status`, `channel`, `deposit_type` | Volumen total de intentos de depósito. |
| `usd_deposits_amount_usd_total`| Counter | `status`, `channel` | Total en dólares procesados. |
| `usd_deposits_duration_seconds`| Histogram | `status`, `channel` | Latencia end-to-end de la operación (P50, P95, P99). |
| `accounts_service_call_duration_seconds` | Histogram | `endpoint`, `http_status` | Tiempo de respuesta del microservicio de cuentas. |
| `accounts_service_circuit_breaker_state` | Gauge | `state` (`0: Closed`, `1: Half-Open`, `2: Open`) | Monitoreo del Circuit Breaker. |

---

## 3. Seguridad y Protección de Datos Financieros

1. **Enmascaramiento de Datos (Data Masking / PII)**:
   - Los números de cuenta en logs se muestran como `ACC-USD-****XXXX`.
   - Los documentos de identidad se enmascaran: `DNI ****3321`.
2. **Prevención de Ataques de Inyección**:
   - Uso de ORM / Parameterized Queries estrictas mediante SQLAlchemy 2.0.
3. **Validación de Payloads Pydantic V2**:
   - Tipado estricto, rechazo de campos desconocidos (`extra = "forbid"`), validación de regex para cuentas (`^ACC-[A-Z]{3}-[0-9]{8}$`).
