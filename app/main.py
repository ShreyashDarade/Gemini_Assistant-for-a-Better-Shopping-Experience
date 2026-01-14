"""
Production-ready FastAPI application for Shopping Assistant.
Features: Rate limiting, CORS, logging, error handling, graceful shutdown.
"""

import asyncio
import logging
import sys
import time
from contextlib import asynccontextmanager
from typing import Callable

import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.models.database import init_db, close_db
from app.routers import chat_router, products_router, media_router, health_router

# Load settings
settings = get_settings()

# Configure structured logging
def configure_logging():
    """Configure production-ready structured logging."""
    
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    if settings.log_format == "json":
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level,
        stream=sys.stdout
    )

configure_logging()
logger = logging.getLogger(__name__)


# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    logger.info("Starting Shopping Assistant API...")
    
    # Startup
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Seed sample data if needed
        from app.utils.seed_data import seed_sample_data
        await seed_sample_data()
        logger.info("Sample data seeded")
        
        logger.info(f"Server ready on {settings.host}:{settings.port}")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    
    try:
        # Cleanup context manager
        from app.services.context_manager import get_context_manager
        context_manager = get_context_manager()
        await context_manager.cleanup_expired_sessions()
        
        # Close database connections
        await close_db()
        logger.info("Database connections closed")
        
    except Exception as e:
        logger.error(f"Shutdown error: {e}")
    
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Shopping Assistant API",
    description="""
    AI-powered shopping assistant backend API.
    
    ## Features
    - **Chat**: Natural language shopping queries with AI responses
    - **Products**: Search, filter, compare, and get recommendations
    - **Media**: Tutorials, troubleshooting guides, and product media
    
    ## Authentication
    Pass session ID via `X-Session-ID` header for conversation continuity.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_timing_header(request: Request, call_next: Callable) -> Response:
    """Add X-Process-Time header to all responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Response:
    """Log all requests for monitoring."""
    start_time = time.time()
    
    # Skip health check logs
    if request.url.path in ["/health", "/live", "/ready"]:
        return await call_next(request)
    
    logger.info(
        f"Request started",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else "unknown",
        }
    )
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    logger.info(
        f"Request completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": int(duration * 1000),
        }
    )
    
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "An internal error occurred",
            "error_code": "INTERNAL_ERROR",
        }
    )


# Include routers
app.include_router(health_router)
app.include_router(chat_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(media_router, prefix="/api/v1")


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to docs."""
    return {
        "message": "Shopping Assistant API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
        log_level=settings.log_level.lower(),
        access_log=True,
    )
