import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from alembic.config import Config
from alembic import command
from sqlalchemy import text

from app.api import auth, users, projects, tasks, audit
from app.core.config import settings
from app.core.logging_config import configure_logging, logger
from app.core.errors import register_exception_handlers
from app.core.limiter import limiter
from app.db.session import engine, SessionLocal
from app.db.seed import seed_first_admin


def run_migrations() -> None:
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Migrations used to run as a bare module-level call in this file --
    i.e. they ran every time `app.main` was *imported*, not just when the
    server actually started. That meant:
      - pytest importing the app for TestClient triggered real schema
        migrations against whatever DATABASE_URL happened to be set.
      - a failed migration crashed the import itself, so there was no
        app object to serve a health check against and no log line
        beyond a raw traceback.
      - under `gunicorn -w 4`, all four workers ran `alembic upgrade
        head` concurrently at boot with no locking, which is a race on
        Postgres (two workers can both see "not yet at head" and both
        attempt the same DDL).

    Moving this into the lifespan handler fixes the first two. The third
    is a deployment concern, not a code one -- migrations should run
    once, as a pre-deploy / release-phase step, before any worker starts.
    The RUN_MIGRATIONS_ON_STARTUP env flag defaults to on for local dev
    /docker-compose convenience but should be turned off in favor of an
    explicit release-phase migration step for any multi-worker deployment.
    """
    configure_logging(settings.LOG_LEVEL)

    if os.environ.get("RUN_MIGRATIONS_ON_STARTUP", "true").lower() == "true":
        try:
            logger.info("Running database migrations...")
            run_migrations()
            logger.info("Migrations complete.")
        except Exception:
            logger.error("Migration failure on startup", exc_info=True)
            raise
    else:
        logger.info("RUN_MIGRATIONS_ON_STARTUP=false; skipping migrations at boot.")

    db = SessionLocal()
    try:
        seed_first_admin(db)
    finally:
        db.close()

    yield

    try:
        engine.dispose()
    except Exception:
        logger.warning("engine.dispose() raised during shutdown; ignoring.", exc_info=True)


app = FastAPI(
    title="Task Management API",
    version="1.0.0",
    description="REST API for managing users, projects, and tasks with JWT auth and role-based access control.",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
app.include_router(audit.router, prefix="/audit-logs", tags=["Audit"])


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Task Management API is running"}


@app.get("/health/db", tags=["Health"])
def health_db():
    """
    The root `/` health check the original app shipped with proves only
    that the ASGI app booted -- it never touches the database, so it
    would report healthy even with a fully broken DB connection. This
    endpoint actually executes a query.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "reachable"}
    except Exception:
        logger.error("DB health check failed", exc_info=True)
        return {"status": "error", "database": "unreachable"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
