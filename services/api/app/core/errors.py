"""Domain exceptions and the handlers that turn them into RFC 9457 responses.

One error shape across every endpoint means the web and mobile clients write
one error handler each instead of one per screen.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base for every expected failure. Unexpected ones become a 500."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"

    def __init__(self, detail: str, *, code: str | None = None) -> None:
        self.detail = detail
        if code:
            self.code = code
        super().__init__(detail)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "permission_denied"


class UpstreamError(AppError):
    """A dependency failed — the AI service, storage, FCM."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "upstream_error"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "detail": exc.detail},
        )
