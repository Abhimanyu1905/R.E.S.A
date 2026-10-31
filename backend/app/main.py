from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.db import get_db

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()

app = FastAPI(
    title="R.E.S.A Support API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", tags=["health"])
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:  # noqa: B008
    """Liveness + readiness probe.

    Returns:
        status: "ok" | "degraded"
        db: "ok" | error message
        version: package version string
    """
    db_status: str
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:  # pragma: no cover
        db_status = str(exc)

    try:
        version = importlib.metadata.version("northwind-support")
    except importlib.metadata.PackageNotFoundError:
        version = "0.1.0"

    overall = "ok" if db_status == "ok" else "degraded"
    return {"status": overall, "db": db_status, "version": version}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, loop="asyncio")
