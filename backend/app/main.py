from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.config import get_settings
from app.core.limiter import limiter
from app.db import get_db
from app.routers import auth, users

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()

app = FastAPI(
    title="R.E.S.A Support API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth and user management routers
app.include_router(auth.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router)
app.include_router(users.router, prefix="/api/v1")


@app.get("/api/docs", include_in_schema=False)
async def api_docs_redirect() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/api/openapi.json", include_in_schema=False)
async def api_openapi_redirect() -> RedirectResponse:
    return RedirectResponse(url="/openapi.json")


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
