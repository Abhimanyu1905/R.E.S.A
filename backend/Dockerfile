FROM python:3.12-slim AS base

# ── system deps ──────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# ── non-root user ─────────────────────────────────────────────────────────────
RUN groupadd --gid 1001 appgroup \
 && useradd  --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# ── python deps (done as root so the venv is owned by root, readable by all) ─
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ── application code ─────────────────────────────────────────────────────────
COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 8000

# The CMD is overridden by docker-compose to run migrations first.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
