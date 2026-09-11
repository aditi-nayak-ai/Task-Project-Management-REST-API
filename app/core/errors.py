import uuid
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.logging_config import logger


def register_exception_handlers(app: FastAPI) -> None:
    """
    Rollback note: we do NOT try to reach into the request-scoped DB
    session from here — FastAPI's dependency-injected Session isn't
    exposed on request.scope. get_db()'s `finally: db.close()` already
    rolls back any pending transaction as part of closing the session,
    so no extra rollback call is needed here; this handler's job is
    purely response shaping and logging.
    """

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.warning("IntegrityError on %s %s: %s", request.method, request.url.path, exc.orig)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "The request conflicts with existing data (duplicate value or invalid reference)."},
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        error_id = uuid.uuid4().hex[:12]
        logger.error("DB error [%s] on %s %s", error_id, request.method, request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Database error.", "error_id": error_id},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        logger.debug("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        error_id = uuid.uuid4().hex[:12]
        logger.error("Unhandled exception [%s] on %s %s", error_id, request.method, request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error.", "error_id": error_id},
        )
