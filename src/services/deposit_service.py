import hashlib
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from src.core.config import settings
from src.core.exceptions import (
    DailyLimitExceededError,
    IdempotencyConflictError,
)
from src.core.logging import logger
from src.domain.models import ChannelType, DepositStatus, IdempotencyStatus
from src.domain.rules import validate_aml_compliance, validate_channel_limits
from src.infrastructure.clients.accounts_client import AccountsServiceClient
from src.infrastructure.db_models import DepositDB
from src.infrastructure.repositories.deposit_repository import DepositRepository
from src.infrastructure.repositories.idempotency_repository import IdempotencyRepository
from src.schemas.deposit_dto import (
    DepositCreateRequest,
    DepositHistoryItemDTO,
    DepositHistoryResponseDTO,
    DepositPaginationDTO,
    DepositResponseDTO,
)


class DepositService:
    def __init__(
        self,
        deposit_repo: DepositRepository,
        idempotency_repo: IdempotencyRepository,
        accounts_client: AccountsServiceClient,
    ):
        self.deposit_repo = deposit_repo
        self.idempotency_repo = idempotency_repo
        self.accounts_client = accounts_client

    def _compute_request_hash(self, req: DepositCreateRequest) -> str:
        data = f"{req.target_account_id}:{req.amount}:{req.currency}:{req.deposit_type.value}"
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    async def process_deposit(
        self,
        request: DepositCreateRequest,
        idempotency_key: str,
        channel: ChannelType,
        correlation_id: str,
    ) -> Tuple[int, DepositResponseDTO]:
        request_hash = self._compute_request_hash(request)

        # 1. Verificación de Idempotencia
        idem_record = await self.idempotency_repo.get_record(idempotency_key)
        if idem_record:
            if idem_record.request_hash != request_hash:
                raise IdempotencyConflictError(idempotency_key)
            if idem_record.status == IdempotencyStatus.COMPLETED and idem_record.response_payload:
                logger.info(
                    f"Respuesta idempotente devuelta para clave {idempotency_key}",
                    extra={"correlation_id": correlation_id},
                )
                return idem_record.response_code or 200, DepositResponseDTO(**idem_record.response_payload)
            if idem_record.status == IdempotencyStatus.PROCESSING:
                raise IdempotencyConflictError(idempotency_key)

        # Registrar clave en estado PROCESSING
        await self.idempotency_repo.create_processing_record(idempotency_key, request_hash)

        # 2. Validaciones locales de negocio
        validate_channel_limits(channel, request.amount, settings)
        validate_aml_compliance(
            request.amount,
            request.aml_declaration.model_dump() if request.aml_declaration else None,
            settings.AML_THRESHOLD_USD,
        )

        # Verificar límite diario acumulado (24h)
        accumulated = await self.deposit_repo.get_daily_accumulated_usd(request.target_account_id)
        if (accumulated + request.amount) > settings.DAILY_LIMIT_USD:
            raise DailyLimitExceededError(
                current_total=accumulated,
                attempt=request.amount,
                limit=settings.DAILY_LIMIT_USD,
            )

        # 3. Guardar registro inicial en Base de Datos
        deposit_id = f"dep_usd_{uuid.uuid4()}"
        deposit_record = DepositDB(
            id=deposit_id,
            target_account_id=request.target_account_id,
            amount=request.amount,
            currency="USD",
            status=DepositStatus.RECEIVED,
            deposit_type=request.deposit_type,
            origin_details=request.origin_details.model_dump() if request.origin_details else {},
            aml_declaration=request.aml_declaration.model_dump() if request.aml_declaration else None,
            correlation_id=correlation_id,
        )
        await self.deposit_repo.create(deposit_record)

        try:
            # 4. Validar cuenta en Microservicio de Cuentas
            await self.deposit_repo.update_status(
                deposit_record,
                DepositStatus.VALIDATING,
                notes="Consultando elegibilidad en Microservicio de Cuentas",
            )
            await self.accounts_client.get_account(request.target_account_id, correlation_id)

            # 5. Orden de Acreditación de Saldo
            await self.deposit_repo.update_status(
                deposit_record,
                DepositStatus.PENDING_CREDIT,
                notes="Enviando orden de abono",
            )
            credit_result = await self.accounts_client.credit_account(
                account_id=request.target_account_id,
                deposit_reference=deposit_id,
                amount=request.amount,
                channel=channel.value,
                correlation_id=correlation_id,
            )

            # 6. Transacción Completada
            tx_id = credit_result.get("transaction_id", f"TX-{uuid.uuid4().hex[:8].upper()}")
            await self.deposit_repo.update_status(
                deposit_record,
                DepositStatus.COMPLETED,
                account_service_tx_id=tx_id,
                notes="Depósito completado y acreditado con éxito",
            )

            response_dto = DepositResponseDTO(
                deposit_id=deposit_record.id,
                status=DepositStatus.COMPLETED,
                target_account_id=deposit_record.target_account_id,
                amount=deposit_record.amount,
                currency="USD",
                fee_applied=Decimal("0.00"),
                net_credited_amount=deposit_record.amount,
                account_service_tx_id=tx_id,
                created_at=deposit_record.created_at,
                completed_at=deposit_record.updated_at,
                receipt_url=f"/api/v1/deposits/usd/{deposit_record.id}/receipt",
            )

            # Guardar en caché de idempotencia
            await self.idempotency_repo.mark_completed(
                idempotency_key=idempotency_key,
                response_code=201,
                response_payload=response_dto.model_dump(mode="json"),
            )

            return 201, response_dto

        except Exception as exc:
            # Actualizar estado según corresponda
            new_status = DepositStatus.FAILED_REVERSED if deposit_record.status == DepositStatus.PENDING_CREDIT else DepositStatus.REJECTED
            await self.deposit_repo.update_status(
                deposit_record,
                new_status,
                error_reason=str(exc),
                notes=f"Operación finalizada con error: {exc}",
            )
            raise exc

    async def get_deposit_by_id(self, deposit_id: str) -> Optional[DepositResponseDTO]:
        dep = await self.deposit_repo.get_by_id(deposit_id)
        if not dep:
            return None
        return DepositResponseDTO(
            deposit_id=dep.id,
            status=dep.status,
            target_account_id=dep.target_account_id,
            amount=dep.amount,
            currency=dep.currency,
            fee_applied=Decimal("0.00"),
            net_credited_amount=dep.amount,
            account_service_tx_id=dep.account_service_tx_id,
            created_at=dep.created_at,
            completed_at=dep.updated_at if dep.status == DepositStatus.COMPLETED else None,
            receipt_url=f"/api/v1/deposits/usd/{dep.id}/receipt" if dep.status == DepositStatus.COMPLETED else None,
            error_reason=dep.error_reason,
        )

    async def list_deposits(
        self,
        target_account_id: Optional[str] = None,
        status: Optional[DepositStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> DepositHistoryResponseDTO:
        items, total = await self.deposit_repo.list_deposits(
            target_account_id=target_account_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        dto_items = [
            DepositHistoryItemDTO(
                deposit_id=item.id,
                amount=item.amount,
                currency=item.currency,
                status=item.status,
                created_at=item.created_at,
            )
            for item in items
        ]
        return DepositHistoryResponseDTO(
            items=dto_items,
            pagination=DepositPaginationDTO(total=total, limit=limit, offset=offset),
        )
