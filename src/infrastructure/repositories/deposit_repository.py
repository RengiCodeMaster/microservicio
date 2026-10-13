from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import DepositStatus
from src.infrastructure.db_models import DepositAuditLogDB, DepositDB


class DepositRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, deposit: DepositDB) -> DepositDB:
        self.session.add(deposit)
        await self.session.flush()

        audit = DepositAuditLogDB(
            deposit_id=deposit.id,
            previous_status=None,
            current_status=deposit.status.value,
            notes="Transacción registrada inicialmente.",
        )
        self.session.add(audit)
        await self.session.commit()
        await self.session.refresh(deposit)
        return deposit

    async def get_by_id(self, deposit_id: str) -> Optional[DepositDB]:
        query = select(DepositDB).where(DepositDB.id == deposit_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def update_status(
        self,
        deposit: DepositDB,
        new_status: DepositStatus,
        account_service_tx_id: Optional[str] = None,
        error_reason: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> DepositDB:
        prev_status = deposit.status.value
        deposit.status = new_status
        if account_service_tx_id:
            deposit.account_service_tx_id = account_service_tx_id
        if error_reason:
            deposit.error_reason = error_reason

        audit = DepositAuditLogDB(
            deposit_id=deposit.id,
            previous_status=prev_status,
            current_status=new_status.value,
            notes=notes or error_reason,
        )
        self.session.add(audit)
        await self.session.commit()
        await self.session.refresh(deposit)
        return deposit

    async def get_daily_accumulated_usd(self, target_account_id: str) -> Decimal:
        since_time = datetime.now(timezone.utc) - timedelta(hours=24)
        query = (
            select(func.coalesce(func.sum(DepositDB.amount), 0))
            .where(DepositDB.target_account_id == target_account_id)
            .where(DepositDB.status == DepositStatus.COMPLETED)
            .where(DepositDB.created_at >= since_time)
        )
        result = await self.session.execute(query)
        val = result.scalar()
        return Decimal(str(val)) if val is not None else Decimal("0.00")

    async def list_deposits(
        self,
        target_account_id: Optional[str] = None,
        status: Optional[DepositStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[DepositDB], int]:
        query = select(DepositDB)
        if target_account_id:
            query = query.where(DepositDB.target_account_id == target_account_id)
        if status:
            query = query.where(DepositDB.status == status)

        # Contar total
        count_query = select(func.count()).select_from(query.subquery())
        total_res = await self.session.execute(count_query)
        total = total_res.scalar() or 0

        # Paginación
        query = query.order_by(DepositDB.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total
