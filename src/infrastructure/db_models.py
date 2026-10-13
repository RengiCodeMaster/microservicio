import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from src.core.database import Base
from src.domain.models import DepositStatus, DepositType, IdempotencyStatus

# Compatibilidad JSON / JSONB tanto en PostgreSQL como SQLite
JsonType = JSON().with_variant(JSONB, "postgresql")


class DepositDB(Base):
    __tablename__ = "usd_deposits"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    target_account_id = Column(String(64), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(Enum(DepositStatus), nullable=False, default=DepositStatus.RECEIVED, index=True)
    deposit_type = Column(Enum(DepositType), nullable=False, default=DepositType.DEP_CASH_USD)
    origin_details = Column(JsonType, nullable=False, default=dict)
    aml_declaration = Column(JsonType, nullable=True)
    account_service_tx_id = Column(String(128), nullable=True)
    correlation_id = Column(String(64), nullable=False)
    error_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class IdempotencyRecordDB(Base):
    __tablename__ = "idempotency_records"

    idempotency_key = Column(String(128), primary_key=True)
    request_hash = Column(String(64), nullable=False)
    status = Column(Enum(IdempotencyStatus), nullable=False, default=IdempotencyStatus.PROCESSING)
    response_code = Column(Integer, nullable=True)
    response_payload = Column(JsonType, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)


class DepositAuditLogDB(Base):
    __tablename__ = "deposit_audit_log"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    deposit_id = Column(String(36), nullable=False, index=True)
    previous_status = Column(String(32), nullable=True)
    current_status = Column(String(32), nullable=False)
    changed_by = Column(String(64), nullable=False, default="SYSTEM")
    notes = Column(Text, nullable=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
