# ---- builder ----
FROM python:3.13-slim AS builder

WORKDIR /app

# System deps needed to build psycopg2-binary / bcrypt wheels on slim images
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- runtime ----
FROM python:3.13-slim AS runtime

WORKDIR /app

# libpq5 is the runtime lib psycopg2 needs (build-essential/libpq-dev were build-only)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Run as a non-root user
RUN addgroup --system app && adduser --system --ingroup app app

COPY --from=builder /install /usr/local
COPY . .

RUN chown -R app:app /app
USER app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health/db || exit 1

# Migrations run inside the app's lifespan (see app/main.py) when
# RUN_MIGRATIONS_ON_STARTUP=true (default). For multi-worker / multi-replica
# production deploys, set RUN_MIGRATIONS_ON_STARTUP=false and run
# `alembic upgrade head` as a separate release-phase step instead, so N
# replicas don't race on DDL at boot.
CMD ["gunicorn", "app.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
