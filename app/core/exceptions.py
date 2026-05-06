"""Custom exceptions and FastAPI exception handlers."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for application-level errors mapped to HTTP responses."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        super().__init__(message or self.__class__.__name__)
        self.message = message or self.__class__.__name__
        if code:
            self.code = code


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class UnknownAssetError(AppError):
    status_code = 400
    code = "unknown_asset"


class CapExceededError(AppError):
    status_code = 429
    code = "daily_cap_exceeded"


class CoinbaseError(AppError):
    """Wraps an error returned by the Coinbase API or SDK."""

    status_code = 502
    code = "coinbase_error"


class InvalidPlanError(AppError):
    status_code = 400
    code = "invalid_plan"


def register_exception_handlers(app: FastAPI) -> None:
    """Register handlers that translate `AppError` subclasses to JSON."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        logger.warning("%s: %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                }
            },
        )
