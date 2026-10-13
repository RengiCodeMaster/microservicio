from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from src.domain.models import DepositStatus, DepositType


class OriginDetailsDTO(BaseModel):
    depositor_id_type: Optional[str] = Field(None, example="DNI")
    depositor_id_number: Optional[str] = Field(None, example="74883321")
    depositor_full_name: Optional[str] = Field(None, example="Carlos Gomez")
    branch_id: Optional[str] = Field(None, example="BR-MIRAFLORES-01")
    teller_id: Optional[str] = Field(None, example="USER-TL-509")


class AmlDeclarationDTO(BaseModel):
    aml_form_id: str = Field(..., example="AML-2026-00492")
    funds_source: str = Field(..., example="SALARY")


class DepositCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_account_id: str = Field(..., min_length=5, max_length=64, example="ACC-USD-88992211")
    amount: Decimal = Field(..., gt=0, decimal_places=2, example=1500.50)
    currency: str = Field("USD", pattern="^USD$", description="Moneda obligatoria: USD")
    deposit_type: DepositType = Field(DepositType.DEP_CASH_USD, example=DepositType.DEP_CASH_USD)
    origin_details: Optional[OriginDetailsDTO] = None
    aml_declaration: Optional[AmlDeclarationDTO] = None
    notes: Optional[str] = Field(None, max_length=255)


class DepositResponseDTO(BaseModel):
    deposit_id: str
    status: DepositStatus
    target_account_id: str
    amount: Decimal
    currency: str
    fee_applied: Decimal = Decimal("0.00")
    net_credited_amount: Decimal
    account_service_tx_id: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    receipt_url: Optional[str] = None
    error_reason: Optional[str] = None


class DepositHistoryItemDTO(BaseModel):
    deposit_id: str
    amount: Decimal
    currency: str
    status: DepositStatus
    created_at: datetime


class DepositPaginationDTO(BaseModel):
    total: int
    limit: int
    offset: int


class DepositHistoryResponseDTO(BaseModel):
    items: List[DepositHistoryItemDTO]
    pagination: DepositPaginationDTO
