"""schemas/user.py – Pydantic schemas for user management."""
from __future__ import annotations

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role_id: int
    role: str
    level: int
    is_active: bool
    created_at: datetime


class UserUpdateRequest(BaseModel):
    role_id: int | None = None
    is_active: bool | None = None
    full_name: str | None = None

