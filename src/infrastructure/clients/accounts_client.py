import time
from decimal import Decimal
from typing import Any, Dict
import httpx

from src.core.config import settings
from src.core.exceptions import (
    AccountCurrencyMismatchError,
    AccountFrozenError,
    AccountNotFoundError,
    AccountsServiceUnavailableError,
)
from src.core.logging import logger
from src.domain.rules import validate_account_eligibility


class SimpleCircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout_sec: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_request(self) -> bool:
        now = time.time()
        if self.state == "OPEN":
            if now - self.last_failure_time > self.recovery_timeout_sec:
                self.state = "HALF_OPEN"
                return True
            return False
        return True

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class AccountsServiceClient:
    def __init__(
        self,
        base_url: str = settings.ACCOUNTS_SERVICE_URL,
        timeout: float = settings.ACCOUNTS_SERVICE_TIMEOUT_SEC,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.circuit_breaker = SimpleCircuitBreaker()

    async def get_account(self, account_id: str, correlation_id: str) -> Dict[str, Any]:
        if not self.circuit_breaker.can_request():
            raise AccountsServiceUnavailableError("Circuit Breaker OPEN hacia el Microservicio de Cuentas.")

        url = f"{self.base_url}/api/v1/accounts/{account_id}"
        headers = {"X-Correlation-ID": correlation_id}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                self.circuit_breaker.record_failure()
                logger.error(f"Falla de red/timeout consultando cuenta {account_id}: {exc}", extra={"correlation_id": correlation_id})
                raise AccountsServiceUnavailableError(f"No se pudo contactar al Microservicio de Cuentas: {exc}")

            if response.status_code == 200:
                self.circuit_breaker.record_success()
                data = response.json()
                validate_account_eligibility(data, account_id)
                return data
            elif response.status_code == 404:
                raise AccountNotFoundError(account_id=account_id)
            elif response.status_code >= 500:
                self.circuit_breaker.record_failure()
                raise AccountsServiceUnavailableError(f"Microservicio de Cuentas respondió {response.status_code}")
            else:
                raise AccountsServiceUnavailableError(f"Error inesperado del servicio de Cuentas: {response.text}")

    async def credit_account(
        self,
        account_id: str,
        deposit_reference: str,
        amount: Decimal,
        channel: str,
        correlation_id: str,
    ) -> Dict[str, Any]:
        if not self.circuit_breaker.can_request():
            raise AccountsServiceUnavailableError("Circuit Breaker OPEN hacia el Microservicio de Cuentas.")

        url = f"{self.base_url}/api/v1/accounts/{account_id}/credits"
        payload = {
            "deposit_reference": deposit_reference,
            "amount": float(amount),
            "currency": "USD",
            "channel": channel,
            "concept": "Depósito en dólares americanos",
        }
        headers = {
            "X-Correlation-ID": correlation_id,
            "Content-Type": "application/json",
        }

        # Intento con reintentos para fallas transitorias de red
        attempts = 0
        max_retries = 3
        last_error = None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while attempts < max_retries:
                attempts += 1
                try:
                    response = await client.post(url, json=payload, headers=headers)
                    if response.status_code in (200, 201):
                        self.circuit_breaker.record_success()
                        return response.json()
                    elif response.status_code == 404:
                        raise AccountNotFoundError(account_id=account_id)
                    elif response.status_code == 422:
                        raise AccountFrozenError(account_id=account_id)
                    elif response.status_code >= 500:
                        last_error = f"Status {response.status_code}: {response.text}"
                    else:
                        raise AccountsServiceUnavailableError(f"Respuesta inesperada: {response.text}")
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    last_error = str(exc)

            self.circuit_breaker.record_failure()
            raise AccountsServiceUnavailableError(f"Agotados {max_retries} reintentos hacia Cuentas: {last_error}")
