import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.circuit_breaker import CircuitBreakerOpenException

logger = logging.getLogger(__name__)

async def circuit_breaker_exception_handler(request: Request, exc: CircuitBreakerOpenException):
    logger.warning(f"Circuit Breaker Open during request to {request.url}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Service Unavailable (Circuit Breaker OPEN)"}
    )

async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception at {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )
