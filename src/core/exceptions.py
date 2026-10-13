from decimal import Decimal
from typing import Optional


class AppException(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        title: str,
        detail: str,
    ):
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.title = title
        self.detail = detail


class IdempotencyConflictError(AppException):
    def __init__(self, key: str):
        super().__init__(
            status_code=409,
            code="IDEMPOTENCY_CONFLICT",
            title="Conflicto de Idempotencia",
            detail=f"La clave de idempotencia '{key}' ya fue utilizada con una solicitud distinta.",
        )


class AccountNotFoundError(AppException):
    def __init__(self, account_id: str):
        super().__init__(
            status_code=404,
            code="ERR_ACCOUNT_NOT_FOUND",
            title="Cuenta no encontrada",
            detail=f"La cuenta destino '{account_id}' no existe en el sistema bancario.",
        )


class AccountCurrencyMismatchError(AppException):
    def __init__(self, account_id: str, current_currency: str):
        super().__init__(
            status_code=422,
            code="ERR_ACCOUNT_CURRENCY_MISMATCH",
            title="Moneda de cuenta incompatible",
            detail=f"La cuenta '{account_id}' opera en divisa '{current_currency}' y no admite depósitos directos en USD.",
        )


class AccountFrozenError(AppException):
    def __init__(self, account_id: str):
        super().__init__(
            status_code=422,
            code="ERR_ACCOUNT_FROZEN",
            title="Cuenta Bloqueada o Inactiva",
            detail=f"La cuenta '{account_id}' se encuentra bloqueada, inactiva o con restricciones para depósitos.",
        )


class AmlDeclarationRequiredError(AppException):
    def __init__(self, amount: Decimal, threshold: Decimal):
        super().__init__(
            status_code=422,
            code="ERR_AML_DECLARATION_REQUIRED",
            title="Declaración Jurada AML Requerida",
            detail=f"Operaciones en USD iguales o mayores a ${threshold:,.2f} requieren el formulario de origen de fondos (aml_declaration). Monto intentado: ${amount:,.2f}.",
        )


class DailyLimitExceededError(AppException):
    def __init__(self, current_total: Decimal, attempt: Decimal, limit: Decimal):
        super().__init__(
            status_code=422,
            code="ERR_DAILY_LIMIT_EXCEEDED",
            title="Límite Diario Acumulado Excedido",
            detail=f"El depósito de ${attempt:,.2f} excede el límite diario permitido (${limit:,.2f}). Total acumulado en las últimas 24h: ${current_total:,.2f}.",
        )


class DepositAmountLimitError(AppException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=422,
            code="ERR_AMOUNT_LIMIT_VIOLATION",
            title="Límite de Monto Inválido",
            detail=detail,
        )


class AccountsServiceUnavailableError(AppException):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            status_code=503,
            code="ERR_ACCOUNTS_SERVICE_UNAVAILABLE",
            title="Servicio de Cuentas No Disponible",
            detail=detail or "El microservicio de cuentas no responde o el Circuit Breaker está abierto.",
        )
