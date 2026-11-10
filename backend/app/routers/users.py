"""routers/users.py – User management endpoints (admin only)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.deps import CurrentUser, require_role
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "",
    response_model=list[UserResponse],
    summary="List all users (Admin only)",
)
async def list_users(
    _: CurrentUser = Depends(require_role(3)),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """Return all users in the system (requires role level >= 3)."""
    stmt = select(User).options(selectinload(User.role)).order_by(User.created_at.asc())
    result = await db.execute(stmt)
    users = result.scalars().all()

    return [
        UserResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role_id=u.role_id,
            role=u.role.name,
            level=u.role.level,
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user's role or status (Admin only)",
)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdateRequest,
    _: CurrentUser = Depends(require_role(3)),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update role, status, or name of a user (requires role level >= 3)."""
    stmt = select(User).options(selectinload(User.role)).where(User.id == user_id)
    user = await db.scalar(stmt)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if payload.role_id is not None:
        role = await db.scalar(select(Role).where(Role.id == payload.role_id))
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role id {payload.role_id} does not exist",
            )
        user.role_id = role.id
        user.role = role

    if payload.is_active is not None:
        user.is_active = payload.is_active

    if payload.full_name is not None:
        user.full_name = payload.full_name

    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role_id=user.role_id,
        role=user.role.name,
        level=user.role.level,
        is_active=user.is_active,
        created_at=user.created_at,
    )

