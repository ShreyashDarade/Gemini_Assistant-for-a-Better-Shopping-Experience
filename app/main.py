"""
Production FastAPI application for the Shopping Assistant.

Features: structured logging with request IDs, Prometheus metrics, rate limiting,
CORS, GZip, security headers, graceful shutdown.
"""

import logging
import sys
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import get_settings
from app.models.database import close_db, init_db
from app.routers import chat_router, health_router, media_router, products_router
from app.services.gemini_client import close_gemini_client

settings = get_settings()
VERSION = "2.0.0"


def configure_logging() -> None:
    """Route stdlib + structlog output through one JSON (or console) renderer."""
    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]
    renderer = (
        structlog.processors.JSONRenderer()
        if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.format_exc_info,
                renderer,
            ],
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())


configure_logging()
logger = structlog.get_logger(__name__)

HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "route", "status"])
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "route"]
)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("startup", version=VERSION, model=settings.ai_model)
    await init_db()

    from app.utils.seed_data import seed_sample_data

    await seed_sample_data()
    yield
    logger.info("shutdown")
    await close_gemini_client()
    await close_db()


app = FastAPI(
    title="Shopping Assistant API",
    description=(
        "AI-powered shopping assistant backend.\n\n"
        "- **Chat**: natural-language shopping queries (REST + WebSocket)\n"
        "- **Products**: search, filter, compare, recommend\n"
        "- **Media**: tutorials and troubleshooting guides\n\n"
        "Pass `X-Session-ID` to keep conversation continuity."
    ),
    version=VERSION,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials and "*" not in settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)

_QUIET_PATHS = {"/health", "/live", "/ready", "/metrics"}


@app.middleware("http")
async def observability(request: Request, call_next):
    """Request ID, timing, access log, metrics and security headers."""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    start = time.perf_counter()
    response: Response | None = None
    try:
        response = await call_next(request)
        return response
    finally:
        elapsed = time.perf_counter() - start
        route = getattr(request.scope.get("route"), "path", "unmatched")
        code = response.status_code if response else 500
        HTTP_REQUESTS.labels(request.method, route, str(code)).inc()
        HTTP_LATENCY.labels(request.method, route).observe(elapsed)
        if response is not None:
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{elapsed:.4f}"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path not in _QUIET_PATHS:
            logger.info(
                "request",
                method=request.method,
                path=request.url.path,
                status=code,
                duration_ms=int(elapsed * 1000),
            )


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "success": False,
            "error": "Invalid request",
            "error_code": "VALIDATION_ERROR",
            "details": [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()],
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "An internal error occurred",
            "error_code": "INTERNAL_ERROR",
        },
    )


app.include_router(health_router)
app.include_router(chat_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(media_router, prefix="/api/v1")

if settings.metrics_enabled:

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "message": "Shopping Assistant API",
        "version": VERSION,
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_config=None,
    )
