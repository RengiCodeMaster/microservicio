from decimal import Decimal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "usd-deposit-service"
    ENV: str = "development"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "sqlite+aiosqlite:///./deposits.db"

    ACCOUNTS_SERVICE_URL: str = "http://localhost:8081"
    ACCOUNTS_SERVICE_TIMEOUT_SEC: float = 5.0

    DAILY_LIMIT_USD: Decimal = Decimal("20000.00")
    AML_THRESHOLD_USD: Decimal = Decimal("10000.00")
    MIN_DEPOSIT_USD: Decimal = Decimal("1.00")
    MAX_DIGITAL_DEPOSIT_USD: Decimal = Decimal("5000.00")
    MAX_BRANCH_DEPOSIT_USD: Decimal = Decimal("50000.00")


settings = Settings()
