"""scripts/seed_users.py – Seed default users for development and testing.

Creates:
- employee@resa.support (role: employee, level: 1)
- agent@resa.support    (role: agent, level: 2)
- admin@resa.support    (role: admin, level: 3)
"""
from __future__ import annotations

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db import AsyncSessionLocal
from app.models.role import Role
from app.models.user import User

SEED_USERS = [
    {
        "email": "employee@resa.support",
        "password": "Employee123!",
        "full_name": "Standard Employee",
        "role_name": "employee",
    },
    {
        "email": "agent@resa.support",
        "password": "Agent123!",
        "full_name": "Tier 2 Agent",
        "role_name": "agent",
    },
    {
        "email": "admin@resa.support",
        "password": "Admin123!",
        "full_name": "System Administrator",
        "role_name": "admin",
    },
]


async def seed_users() -> None:
    async with AsyncSessionLocal() as session:
        # Fetch all roles
        roles_result = await session.execute(select(Role))
        roles_by_name = {r.name: r for r in roles_result.scalars().all()}

        print("=" * 60)
        print("SEEDING USERS")
        print("=" * 60)

        for user_data in SEED_USERS:
            role_name = user_data["role_name"]
            role = roles_by_name.get(role_name)
            if not role:
                print(f"Error: Role '{role_name}' not found in database!")
                continue

            email = user_data["email"]
            pwd_hash = get_password_hash(user_data["password"])

            stmt = select(User).where(User.email == email)
            existing = (await session.execute(stmt)).scalar_one_or_none()

            if existing:
                existing.password_hash = pwd_hash
                existing.full_name = user_data["full_name"]
                existing.role_id = role.id
                existing.is_active = True
                print(f"[UPDATED] {email:<26} -> role: {role.name:<8} (level {role.level})")
            else:
                new_user = User(
                    email=email,
                    password_hash=pwd_hash,
                    full_name=user_data["full_name"],
                    role_id=role.id,
                    is_active=True,
                )
                session.add(new_user)
                print(f"[CREATED] {email:<26} -> role: {role.name:<8} (level {role.level})")

        await session.commit()
        print("=" * 60)
        print("Seed credentials summary:")
        for u in SEED_USERS:
            print(f"  {u['email']:<26} | password: {u['password']} | role: {u['role_name']}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed_users())

