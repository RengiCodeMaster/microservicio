import uuid
import pytest
import respx
import httpx
from src.core.config import settings

pytestmark = pytest.mark.asyncio


async def test_health_probes(client):
    res_live = await client.get("/health/live")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "UP"

    res_ready = await client.get("/health/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "READY"


@respx.mock
async def test_successful_usd_deposit(client):
    account_id = "ACC-USD-88992211"
    key = str(uuid.uuid4())

    # Mock del Microservicio de Cuentas
    respx.get(f"{settings.ACCOUNTS_SERVICE_URL}/api/v1/accounts/{account_id}").mock(
        return_value=httpx.Response(
            200,
            json={
                "account_id": account_id,
                "status": "ACTIVE",
                "currency": "USD",
                "allows_deposits": True,
                "is_frozen": False,
            },
        )
    )
    respx.post(f"{settings.ACCOUNTS_SERVICE_URL}/api/v1/accounts/{account_id}/credits").mock(
        return_value=httpx.Response(
            201,
            json={
                "transaction_id": "ACC-TX-990011",
                "account_id": account_id,
                "new_balance": 4500.50,
                "credited_amount": 1500.50,
                "currency": "USD",
                "status": "SUCCESS",
            },
        )
    )

    payload = {
        "target_account_id": account_id,
        "amount": 1500.50,
        "currency": "USD",
        "deposit_type": "DEP_CASH_USD",
        "origin_details": {
            "depositor_id_type": "DNI",
            "depositor_id_number": "74883321",
            "depositor_full_name": "Carlos Gomez",
        },
    }
    headers = {
        "X-Idempotency-Key": key,
        "X-Channel": "BRANCH",
    }

    res = await client.post("/api/v1/deposits/usd", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["amount"] == "1500.50"
    assert data["currency"] == "USD"
    assert data["account_service_tx_id"] == "ACC-TX-990011"
    deposit_id = data["deposit_id"]

    # Consultar por ID
    res_get = await client.get(f"/api/v1/deposits/usd/{deposit_id}")
    assert res_get.status_code == 200
    assert res_get.json()["deposit_id"] == deposit_id

    # Consultar comprobante
    res_receipt = await client.get(f"/api/v1/deposits/usd/{deposit_id}/receipt")
    assert res_receipt.status_code == 200
    assert res_receipt.json()["operation_code"] == "ACC-TX-990011"


@respx.mock
async def test_idempotency_behavior(client):
    account_id = "ACC-USD-88992211"
    key = str(uuid.uuid4())

    respx.get(f"{settings.ACCOUNTS_SERVICE_URL}/api/v1/accounts/{account_id}").mock(
        return_value=httpx.Response(
            200,
            json={"account_id": account_id, "status": "ACTIVE", "currency": "USD", "allows_deposits": True, "is_frozen": False},
        )
    )
    respx.post(f"{settings.ACCOUNTS_SERVICE_URL}/api/v1/accounts/{account_id}/credits").mock(
        return_value=httpx.Response(201, json={"transaction_id": "ACC-TX-IDEM", "status": "SUCCESS"})
    )

    payload = {
        "target_account_id": account_id,
        "amount": 200.00,
        "currency": "USD",
        "deposit_type": "DEP_CASH_USD",
    }
    headers = {"X-Idempotency-Key": key, "X-Channel": "BRANCH"}

    # Primera llamada
    res1 = await client.post("/api/v1/deposits/usd", json=payload, headers=headers)
    assert res1.status_code == 201

    # Segunda llamada idéntica -> debe retornar en caché con 201
    res2 = await client.post("/api/v1/deposits/usd", json=payload, headers=headers)
    assert res2.status_code == 201
    assert res2.json()["deposit_id"] == res1.json()["deposit_id"]

    # Tercera llamada con misma clave pero DIFERENTE monto -> debe dar 409 Conflict
    payload_conflict = {**payload, "amount": 300.00}
    res3 = await client.post("/api/v1/deposits/usd", json=payload_conflict, headers=headers)
    assert res3.status_code == 409
    assert res3.json()["code"] == "IDEMPOTENCY_CONFLICT"


@respx.mock
async def test_currency_mismatch_rejection(client):
    account_id = "ACC-EUR-100293"
    key = str(uuid.uuid4())

    respx.get(f"{settings.ACCOUNTS_SERVICE_URL}/api/v1/accounts/{account_id}").mock(
        return_value=httpx.Response(
            200,
            json={"account_id": account_id, "status": "ACTIVE", "currency": "EUR", "allows_deposits": True, "is_frozen": False},
        )
    )

    payload = {
        "target_account_id": account_id,
        "amount": 100.00,
        "currency": "USD",
        "deposit_type": "DEP_CASH_USD",
    }
    headers = {"X-Idempotency-Key": key, "X-Channel": "BRANCH"}

    res = await client.post("/api/v1/deposits/usd", json=payload, headers=headers)
    assert res.status_code == 422
    data = res.json()
    assert data["code"] == "ERR_ACCOUNT_CURRENCY_MISMATCH"


async def test_aml_declaration_required(client):
    key = str(uuid.uuid4())
    payload = {
        "target_account_id": "ACC-USD-9900",
        "amount": 12000.00,  # >= 10,000 USD
        "currency": "USD",
        "deposit_type": "DEP_CASH_USD",
        # aml_declaration ausente
    }
    headers = {"X-Idempotency-Key": key, "X-Channel": "BRANCH"}

    res = await client.post("/api/v1/deposits/usd", json=payload, headers=headers)
    assert res.status_code == 422
    assert res.json()["code"] == "ERR_AML_DECLARATION_REQUIRED"


async def test_daily_limit_exceeded(client):
    key = str(uuid.uuid4())
    payload = {
        "target_account_id": "ACC-USD-9900",
        "amount": 25000.00,  # Excede límite diario de $20,000 USD
        "currency": "USD",
        "deposit_type": "DEP_CASH_USD",
        "aml_declaration": {
            "aml_form_id": "AML-001",
            "funds_source": "BUSINESS",
        },
    }
    headers = {"X-Idempotency-Key": key, "X-Channel": "BRANCH"}

    res = await client.post("/api/v1/deposits/usd", json=payload, headers=headers)
    assert res.status_code == 422
    assert res.json()["code"] == "ERR_DAILY_LIMIT_EXCEEDED"


@respx.mock
async def test_account_frozen_rejection(client):
    account_id = "ACC-FROZEN-001"
    key = str(uuid.uuid4())

    respx.get(f"{settings.ACCOUNTS_SERVICE_URL}/api/v1/accounts/{account_id}").mock(
        return_value=httpx.Response(
            200,
            json={"account_id": account_id, "status": "FROZEN", "currency": "USD", "allows_deposits": False, "is_frozen": True},
        )
    )

    payload = {
        "target_account_id": account_id,
        "amount": 250.00,
        "currency": "USD",
        "deposit_type": "DEP_CASH_USD",
    }
    headers = {"X-Idempotency-Key": key, "X-Channel": "BRANCH"}

    res = await client.post("/api/v1/deposits/usd", json=payload, headers=headers)
    assert res.status_code == 422
    assert res.json()["code"] == "ERR_ACCOUNT_FROZEN"


@respx.mock
async def test_accounts_service_unavailable(client):
    account_id = "ACC-USD-DOWN"
    key = str(uuid.uuid4())

    # Simular caída / error 503 continuo
    respx.get(f"{settings.ACCOUNTS_SERVICE_URL}/api/v1/accounts/{account_id}").mock(
        return_value=httpx.Response(503, text="Service Unavailable")
    )

    payload = {
        "target_account_id": account_id,
        "amount": 100.00,
        "currency": "USD",
        "deposit_type": "DEP_CASH_USD",
    }
    headers = {"X-Idempotency-Key": key, "X-Channel": "BRANCH"}

    res = await client.post("/api/v1/deposits/usd", json=payload, headers=headers)
    assert res.status_code == 503
    assert res.json()["code"] == "ERR_ACCOUNTS_SERVICE_UNAVAILABLE"


@respx.mock
async def test_idempotency_key_standard_header(client):
    account_id = "ACC-USD-88992211"
    key = str(uuid.uuid4())

    respx.get(f"{settings.ACCOUNTS_SERVICE_URL}/api/v1/accounts/{account_id}").mock(
        return_value=httpx.Response(
            200,
            json={
                "account_id": account_id,
                "status": "ACTIVE",
                "currency": "USD",
                "allows_deposits": True,
                "is_frozen": False,
            },
        )
    )
    respx.post(f"{settings.ACCOUNTS_SERVICE_URL}/api/v1/accounts/{account_id}/credits").mock(
        return_value=httpx.Response(
            201,
            json={
                "transaction_id": "ACC-TX-5544",
                "account_id": account_id,
                "new_balance": 1250.00,
                "credited_amount": 250.00,
                "currency": "USD",
                "status": "SUCCESS",
            },
        )
    )

    payload = {
        "target_account_id": account_id,
        "amount": 250.00,
        "currency": "USD",
        "deposit_type": "DEP_TRANSFER_USD",
    }
    # Enviar usando el encabezado estándar de Billetera: Idempotency-Key
    headers = {
        "Idempotency-Key": key,
        "X-Channel": "PARTNER",
    }

    res = await client.post("/api/v1/deposits/usd", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["status"] == "COMPLETED"


async def test_missing_idempotency_key(client):
    payload = {
        "target_account_id": "ACC-USD-88992211",
        "amount": 100.00,
        "currency": "USD",
        "deposit_type": "DEP_CASH_USD",
    }
    # Sin ninguna cabecera de idempotencia
    res = await client.post("/api/v1/deposits/usd", json=payload)
    assert res.status_code == 422
    assert res.json()["code"] == "ERR_MISSING_IDEMPOTENCY_KEY"
