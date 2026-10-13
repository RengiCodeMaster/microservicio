from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.infrastructure.clients.accounts_client import AccountsServiceClient
from src.infrastructure.repositories.deposit_repository import DepositRepository
from src.infrastructure.repositories.idempotency_repository import IdempotencyRepository
from src.services.deposit_service import DepositService

# Singleton client para compartir el estado del Circuit Breaker
_accounts_client_singleton = AccountsServiceClient()


def get_accounts_client() -> AccountsServiceClient:
    return _accounts_client_singleton


def get_deposit_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    accounts_client: Annotated[AccountsServiceClient, Depends(get_accounts_client)],
) -> DepositService:
    deposit_repo = DepositRepository(session)
    idempotency_repo = IdempotencyRepository(session)
    return DepositService(
        deposit_repo=deposit_repo,
        idempotency_repo=idempotency_repo,
        accounts_client=accounts_client,
    )
