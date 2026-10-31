"""Alembic environment – async SQLAlchemy with psycopg3.

Key decisions:
- Uses run_async_migrations() so the same async engine as the app is used.
- Imports app.models so autogenerate can diff against all mapped tables.
- DATABASE_URL is read from the environment / .env via pydantic-settings.
  The URL is rewritten to the psycopg async driver if needed.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import TYPE_CHECKING

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.config import get_settings

# ── Load all models so their metadata is visible to autogenerate ─────────────
from app.models import Base  # noqa: F401 – side-effect: registers all tables

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_url() -> str:
    """Return an async-compatible database URL."""
    settings = get_settings()
    url = settings.DATABASE_URL
    # Rewrite to psycopg async driver
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    url = url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


# ── Offline mode (generates SQL without a live DB) ───────────────────────────
def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (async) ───────────────────────────────────────────────────────
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
