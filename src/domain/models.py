from enum import Enum


class DepositStatus(str, Enum):
    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    PENDING_CREDIT = "PENDING_CREDIT"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED_REVERSED = "FAILED_REVERSED"


class DepositType(str, Enum):
    DEP_CASH_USD = "DEP_CASH_USD"
    DEP_TRANSFER_USD = "DEP_TRANSFER_USD"


class ChannelType(str, Enum):
    BRANCH = "BRANCH"
    ATM = "ATM"
    WEB = "WEB"
    MOBILE = "MOBILE"
    PARTNER = "PARTNER"


class IdempotencyStatus(str, Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
