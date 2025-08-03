from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from app.core.config import settings
from app.api.v1.router import api_router
from app.database.connection import create_tables, db_manager
from app.schemas.response import HealthCheckResponse, ErrorResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/app.log") if settings.environment != "test" else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    try:
        await create_tables()
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.service_name}")


# Create FastAPI application
app = FastAPI(
    title="Resume Builder Service",
    description="JobReadyNow Resume Builder Microservice - Create, manage, and export professional resumes",
    version=settings.service_version,
    lifespan=lifespan,
    debug=settings.debug,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.jobreadynow.com", "*"]
)


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")

    error_codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR"
    }

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=error_codes.get(exc.status_code, "HTTP_ERROR"),
            message=exc.detail,
            timestamp=datetime.utcnow()
        ).dict()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred" if not settings.debug else str(exc),
            timestamp=datetime.utcnow()
        ).dict()
    )


# Health check endpoints
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Basic health check"""
    return HealthCheckResponse(
        status="healthy",
        service=settings.service_name,
        version=settings.service_version
    )


@app.get("/health/detailed", response_model=HealthCheckResponse)
async def detailed_health_check():
    """Detailed health check with dependencies"""
    try:
        # Check database
        db_health = await db_manager.health_check()

        checks = {
            "database": db_health,
            "environment": {
                "status": "healthy",
                "environment": settings.environment,
                "debug": settings.debug
            }
        }

        # Determine overall status
        overall_status = "healthy"
        if db_health.get("status") != "healthy":
            overall_status = "unhealthy"

        return HealthCheckResponse(
            status=overall_status,
            service=settings.service_name,
            version=settings.service_version,
            checks=checks
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            service=settings.service_name,
            version=settings.service_version,
            checks={"error": str(e)}
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled",
        "health": "/health"
    }


# Rate limited endpoints
@app.get("/ping")
@limiter.limit("10/minute")
async def ping(request: Request):
    """Simple ping endpoint with rate limiting"""
    return {"message": "pong", "timestamp": datetime.utcnow()}


# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Add middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    start_time = datetime.utcnow()

    # Log request
    logger.info(f"Request: {request.method} {request.url}")

    # Process request
    response = await call_next(request)

    # Log response
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"Response: {response.status_code} - {duration:.3f}s")

    return response


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=settings.debug
    )