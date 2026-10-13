from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_accounts_client
from src.core.database import get_db_session
from src.infrastructure.clients.accounts_client import AccountsServiceClient

router = APIRouter(prefix="/health", tags=["Health & Monitoring"])


@router.get("/live", summary="Liveness Probe para Kubernetes / Docker")
async def liveness():
    return {"status": "UP", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/ready", summary="Readiness Probe para Kubernetes / Balanceadores")
async def readiness(
    session: AsyncSession = Depends(get_db_session),
    accounts_client: AccountsServiceClient = Depends(get_accounts_client),
):
    db_status = "DOWN"
    try:
        await session.execute(text("SELECT 1;"))
        db_status = "UP"
    except Exception:
        db_status = "DOWN"

    cb_state = accounts_client.circuit_breaker.state
    is_ready = db_status == "UP" and cb_state != "OPEN"

    payload = {
        "status": "READY" if is_ready else "NOT_READY",
        "dependencies": {
            "database": db_status,
            "accounts_service_circuit_breaker": cb_state,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=payload)
