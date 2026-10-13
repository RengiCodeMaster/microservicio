from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import IdempotencyStatus
from src.infrastructure.db_models import IdempotencyRecordDB


class IdempotencyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_record(self, idempotency_key: str) -> Optional[IdempotencyRecordDB]:
        query = select(IdempotencyRecordDB).where(IdempotencyRecordDB.idempotency_key == idempotency_key)
        result = await self.session.execute(query)
        record = result.scalars().first()
        if record:
            now_utc = datetime.now(timezone.utc)
            record_expiry = record.expires_at
            if record_expiry.tzinfo is None:
                record_expiry = record_expiry.replace(tzinfo=timezone.utc)
            if record_expiry < now_utc:
                # Expirado
                return None
        return record

    async def create_processing_record(self, idempotency_key: str, request_hash: str) -> IdempotencyRecordDB:
        record = IdempotencyRecordDB(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            status=IdempotencyStatus.PROCESSING,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def mark_completed(
        self,
        idempotency_key: str,
        response_code: int,
        response_payload: Dict[str, Any],
    ) -> None:
        record = await self.get_record(idempotency_key)
        if record:
            record.status = IdempotencyStatus.COMPLETED
            record.response_code = response_code
            record.response_payload = response_payload
            await self.session.commit()
