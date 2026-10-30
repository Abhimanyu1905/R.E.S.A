"""Declarative base shared by all models."""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Single metadata registry; imported by every model and by Alembic env.py."""
