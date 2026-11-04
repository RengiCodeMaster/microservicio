import uuid
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status

from src.api.dependencies import get_deposit_service
from src.core.exceptions import AppException
from src.domain.models import ChannelType, DepositStatus
from src.schemas.deposit_dto import (
    DepositCreateRequest,
    DepositHistoryResponseDTO,
    DepositResponseDTO,
)
from src.services.deposit_service import DepositService

router = APIRouter(prefix="/api/v1/deposits/usd", tags=["USD Deposits"])


def get_idempotency_key(
    x_idempotency_key: Annotated[
        Optional[str],
        Header(alias="X-Idempotency-Key", description="UUIDv4 único por transacción (estándar bancario)"),
    ] = None,
    idempotency_key: Annotated[
        Optional[str],
        Header(alias="Idempotency-Key", description="UUIDv4 único por transacción (estándar IETF / Billetera)"),
    ] = None,
) -> str:
    key = x_idempotency_key or idempotency_key
    if not key:
        raise AppException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="ERR_MISSING_IDEMPOTENCY_KEY",
            title="Cabecera de Idempotencia Requerida",
            detail="Se requiere la cabecera 'X-Idempotency-Key' o 'Idempotency-Key' con un UUIDv4 válido.",
        )
    return key


@router.post(
    "",
    response_model=DepositResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Procesar un depósito en dólares (USD)",
    description="Inicia, valida y acredita fondos en USD hacia una cuenta destino cumpliendo reglas bancarias, AML e idempotencia. Acepta tanto 'X-Idempotency-Key' como 'Idempotency-Key'.",
)
async def create_usd_deposit(
    request: DepositCreateRequest,
    response: Response,
    service: Annotated[DepositService, Depends(get_deposit_service)],
    idempotency_key: Annotated[str, Depends(get_idempotency_key)],
    x_channel: Annotated[ChannelType, Header(alias="X-Channel", description="Canal de operación")] = ChannelType.BRANCH,
    x_correlation_id: Annotated[Optional[str], Header(alias="X-Correlation-ID", description="ID de trazabilidad")] = None,
):
    correlation_id = x_correlation_id or str(uuid.uuid4())
    status_code, result = await service.process_deposit(
        request=request,
        idempotency_key=idempotency_key,
        channel=x_channel,
        correlation_id=correlation_id,
    )
    response.status_code = status_code
    return result


@router.get(
    "/{deposit_id}",
    response_model=DepositResponseDTO,
    summary="Consultar estado de depósito por ID",
)
async def get_usd_deposit(
    deposit_id: str,
    service: Annotated[DepositService, Depends(get_deposit_service)],
):
    deposit = await service.get_deposit_by_id(deposit_id)
    if not deposit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Depósito con ID '{deposit_id}' no encontrado.",
        )
    return deposit


@router.get(
    "",
    response_model=DepositHistoryResponseDTO,
    summary="Listar historial de depósitos en dólares",
)
async def list_usd_deposits(
    service: Annotated[DepositService, Depends(get_deposit_service)],
    target_account_id: Optional[str] = Query(None, description="Filtrar por número de cuenta"),
    status_filter: Optional[DepositStatus] = Query(None, alias="status", description="Filtrar por estado"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await service.list_deposits(
        target_account_id=target_account_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{deposit_id}/receipt",
    summary="Descargar comprobante digital de depósito",
)
async def get_deposit_receipt(
    deposit_id: str,
    service: Annotated[DepositService, Depends(get_deposit_service)],
):
    deposit = await service.get_deposit_by_id(deposit_id)
    if not deposit:
        raise HTTPException(status_code=404, detail="Depósito no encontrado")

    return {
        "institution": "BANCO FINANCIERO DE LA NUBE",
        "voucher_title": "CONSTANCIA DE DEPÓSITO EN MONEDA EXTRANJERA (USD)",
        "deposit_id": deposit.deposit_id,
        "account_id": deposit.target_account_id,
        "amount": f"{deposit.amount} USD",
        "status": deposit.status.value,
        "operation_code": deposit.account_service_tx_id,
        "timestamp": deposit.completed_at or deposit.created_at,
    }
