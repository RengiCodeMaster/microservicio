import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        if hasattr(record, "deposit_id"):
            log_entry["deposit_id"] = record.deposit_id
        if hasattr(record, "target_account_id"):
            acc = str(record.target_account_id)
            log_entry["target_account_id_masked"] = f"{acc[:7]}****{acc[-4:]}" if len(acc) >= 11 else "****"
        if hasattr(record, "amount"):
            log_entry["amount"] = float(record.amount)
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logger(log_level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("usd_deposit_service")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    return logger


logger = setup_logger()
