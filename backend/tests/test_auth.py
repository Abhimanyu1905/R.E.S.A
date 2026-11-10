"""tests/test_auth.py – Authentication and authorization unit and integration tests.

Tests:
1. Duplicate email returns 409
2. Bad password returns 401
3. Expired token returns 401
4. Tampered token returns 401
5. Employee calling admin route returns 403
6. Role change takes effect without re-login
7. /auth/me returns {id, email, full_name, role, level}
8. /auth/refresh returns fresh tokens
"""
from __future__ import annotations

from datetime import timedelta
import sys
from typing import TYPE_CHECKING
import uuid

if sys.platform == "win32":
    import asyncio
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from httpx import ASGITransport, AsyncClient
import pytest
from sqlalchemy import delete, select

from app.core.security import create_access_token
from app.db import AsyncSessionLocal
from app.main import app
from app.models.role import Role
from app.models.user import User

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
async def cleanup_test_users() -> AsyncGenerator[None, None]:
    """Clean up any test users created during test runs."""
    yield
    async with AsyncSessionLocal() as session:
        stmt = delete(User).where(User.email.like("test_%@example.com"))
        await session.execute(stmt)
        await session.commit()


@pytest.mark.asyncio
async def test_register_duplicate_email_409(client: AsyncClient) -> None:
    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": test_email,
        "password": "ValidPassword123!",
        "full_name": "Test User",
    }

    # 1. First registration succeeds (201)
    res1 = await client.post("/auth/register", json=payload)
    assert res1.status_code == 201, res1.text
    data1 = res1.json()
    assert data1["email"] == test_email
    assert data1["role"] == "employee"
    assert data1["level"] == 1

    # 2. Duplicate registration fails (409)
    res2 = await client.post("/auth/register", json=payload)
    assert res2.status_code == 409, res2.text
    assert "already registered" in res2.text.lower()


@pytest.mark.asyncio
async def test_login_bad_password_401(client: AsyncClient) -> None:
    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/auth/register",
        json={"email": test_email, "password": "CorrectPassword123!", "full_name": "Test User"},
    )

    # Attempt login with bad password
    res = await client.post(
        "/auth/login",
        json={"email": test_email, "password": "WrongPassword!"},
    )
    assert res.status_code == 401, res.text


@pytest.mark.asyncio
async def test_expired_token_401(client: AsyncClient) -> None:
    user_id = uuid.uuid4()
    # Create an access token that expired 10 seconds ago
    expired_token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(seconds=-10),
    )

    res = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401, res.text
    assert "expired" in res.text.lower()


@pytest.mark.asyncio
async def test_tampered_token_401(client: AsyncClient) -> None:
    user_id = uuid.uuid4()
    valid_token = create_access_token(subject=user_id)
    # Tamper with signature
    tampered_token = valid_token[:-4] + "xxxx"

    res = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert res.status_code == 401, res.text


@pytest.mark.asyncio
async def test_employee_calling_admin_route_403(client: AsyncClient) -> None:
    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/auth/register",
        json={"email": test_email, "password": "Password123!", "full_name": "Employee One"},
    )

    # Login to get employee token
    login_res = await client.post(
        "/auth/login",
        json={"email": test_email, "password": "Password123!"},
    )
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["access_token"]

    # Call admin route /users
    admin_res = await client.get(
        "/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert admin_res.status_code == 403, admin_res.text
    assert "forbidden" in admin_res.text.lower() or "insufficient" in admin_res.text.lower()


@pytest.mark.asyncio
async def test_role_change_takes_effect_without_relogin(client: AsyncClient) -> None:
    """Verifies that changing a user's role in the DB immediately upgrades permissions.

    The client uses the SAME access token without re-logging in.
    """
    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = await client.post(
        "/auth/register",
        json={"email": test_email, "password": "Password123!", "full_name": "Upgradable User"},
    )
    user_id = reg_res.json()["id"]

    # 1. Log in as employee -> get token
    login_res = await client.post(
        "/auth/login",
        json={"email": test_email, "password": "Password123!"},
    )
    token = login_res.json()["access_token"]

    # 2. Call admin route -> expect 403 Forbidden
    res_before = await client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert res_before.status_code == 403, res_before.text

    # 3. Elevate user role in DB to admin (level 3)
    async with AsyncSessionLocal() as session:
        admin_role = (
            await session.execute(select(Role).where(Role.level == 3))
        ).scalar_one()
        user = (
            await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
        ).scalar_one()
        user.role_id = admin_role.id
        await session.commit()

    # 4. Call admin route using the EXACT SAME token without re-login -> expect 200 OK!
    res_after = await client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert res_after.status_code == 200, res_after.text
    user_list = res_after.json()
    assert isinstance(user_list, list)
    assert any(u["id"] == user_id for u in user_list)


@pytest.mark.asyncio
async def test_auth_me_schema(client: AsyncClient) -> None:
    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/auth/register",
        json={"email": test_email, "password": "Password123!", "full_name": "Profile User"},
    )

    login_res = await client.post(
        "/auth/login",
        json={"email": test_email, "password": "Password123!"},
    )
    token = login_res.json()["access_token"]

    me_res = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200, me_res.text
    data = me_res.json()
    assert set(data.keys()) == {"id", "email", "full_name", "role", "level"}
    assert data["email"] == test_email
    assert data["full_name"] == "Profile User"
    assert data["role"] == "employee"
    assert data["level"] == 1


@pytest.mark.asyncio
async def test_refresh_token_flow(client: AsyncClient) -> None:
    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/auth/register",
        json={"email": test_email, "password": "Password123!", "full_name": "Refresh User"},
    )

    login_res = await client.post(
        "/auth/login",
        json={"email": test_email, "password": "Password123!"},
    )
    tokens = login_res.json()
    refresh_token = tokens["refresh_token"]

    # Exchange refresh token for fresh tokens
    refresh_res = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200, refresh_res.text
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens

    # Verify new access token works
    me_res = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
    )
    assert me_res.status_code == 200, me_res.text

