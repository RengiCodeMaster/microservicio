import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.health import router as health_router
from src.api.v1.deposits import router as deposits_router
from src.core.config import settings
from src.core.database import Base, engine
from src.core.exceptions import AppException
from src.core.logging import logger
from src.schemas.problem_details import ProblemDetails


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialización de tablas en la base de datos
    logger.info("Inicializando esquema de base de datos...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Microservicio de Depósitos USD iniciado correctamente.")
    yield
    logger.info("Cerrando conexiones de base de datos...")
    await engine.dispose()


app = FastAPI(
    title="USD Deposit Microservice",
    version="1.0.0",
    description="Microservicio bancario para la gestión, validación y acreditación de depósitos en dólares americanos (USD).",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware de Correlación y Métricas de Duración
@app.middleware("http")
async def correlation_and_metrics_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    start_time = time.perf_counter()

    response = await call_next(request)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Correlation-ID"] = correlation_id

    # Log estructurado
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({elapsed_ms:.2f}ms)",
        extra={
            "correlation_id": correlation_id,
            "duration_ms": round(elapsed_ms, 2),
        },
    )
    return response


# Manejador de Excepciones Financieras (RFC 7807)
@app.exception_handler(AppException)
async def handle_app_exception(request: Request, exc: AppException):
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    problem = ProblemDetails(
        type=f"https://banco.com/errors/{exc.code}",
        title=exc.title,
        status=exc.status_code,
        detail=exc.detail,
        instance=str(request.url.path),
        code=exc.code,
        correlation_id=correlation_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(mode="json"),
        headers={"Content-Type": "application/problem+json"},
    )


# Manejador de Errores de Validación Pydantic (RFC 7807)
@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    errors_str = "; ".join([f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in exc.errors()])
    problem = ProblemDetails(
        type="https://banco.com/errors/VALIDATION_ERROR",
        title="Error de validación en la solicitud",
        status=422,
        detail=errors_str,
        instance=str(request.url.path),
        code="ERR_PAYLOAD_VALIDATION",
        correlation_id=correlation_id,
    )
    return JSONResponse(
        status_code=422,
        content=problem.model_dump(mode="json"),
        headers={"Content-Type": "application/problem+json"},
    )


# Registrar Routers
app.include_router(health_router)
app.include_router(deposits_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
