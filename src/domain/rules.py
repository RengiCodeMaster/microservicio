from decimal import Decimal
from typing import Any, Dict, Optional

from src.core.config import Settings
from src.core.exceptions import (
    AccountCurrencyMismatchError,
    AccountFrozenError,
    AmlDeclarationRequiredError,
    DepositAmountLimitError,
)
from src.domain.models import ChannelType


def validate_channel_limits(channel: ChannelType, amount: Decimal, cfg: Settings) -> None:
    if amount < cfg.MIN_DEPOSIT_USD:
        raise DepositAmountLimitError(f"El monto mínimo de depósito es ${cfg.MIN_DEPOSIT_USD:,.2f} USD.")

    if channel in (ChannelType.WEB, ChannelType.MOBILE):
        if amount > cfg.MAX_DIGITAL_DEPOSIT_USD:
            raise DepositAmountLimitError(
                f"El monto máximo para canal digital ({channel.value}) es ${cfg.MAX_DIGITAL_DEPOSIT_USD:,.2f} USD."
            )
    else:
        if amount > cfg.MAX_BRANCH_DEPOSIT_USD:
            raise DepositAmountLimitError(
                f"El monto máximo para depósito presencial ({channel.value}) es ${cfg.MAX_BRANCH_DEPOSIT_USD:,.2f} USD."
            )


def validate_aml_compliance(amount: Decimal, aml_data: Optional[Dict[str, Any]], threshold: Decimal) -> None:
    if amount >= threshold:
        if not aml_data or not aml_data.get("aml_form_id"):
            raise AmlDeclarationRequiredError(amount=amount, threshold=threshold)


def validate_account_eligibility(account: Dict[str, Any], account_id: str) -> None:
    status = str(account.get("status", "")).upper()
    if status != "ACTIVE":
        raise AccountFrozenError(account_id=account_id)

    if account.get("is_frozen", False):
        raise AccountFrozenError(account_id=account_id)

    if not account.get("allows_deposits", True):
        raise AccountFrozenError(account_id=account_id)

    currency = str(account.get("currency", "")).upper()
    if currency not in ("USD", "MULTI_CURRENCY"):
        raise AccountCurrencyMismatchError(account_id=account_id, current_currency=currency)
