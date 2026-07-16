from logging import getLogger

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import BaseAppException

logger = getLogger(__name__)


async def app_exception_handler(
    request: Request, exc: BaseAppException
) -> JSONResponse:
    """
    Universal custom error interceptor
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "payload": exc.payload,
        },
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Universal global unexpected error interceptor
    """
    logger.exception(f"Unhandled exception occurred: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "Internal Server Error. Try again later",
            "payload": {},
        },
    )
