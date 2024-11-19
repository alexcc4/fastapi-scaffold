import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.db.redis import get_token_key
from app.models.user import User


async def test_register_new_user(
    client: AsyncClient,
    db: AsyncSession,
    redis_conn: Redis,
    fake_clerk: dict,
    mock_clerk_success,
    auth_headers,
):
    response = await client.post(
        "/api/v1/auth/login",
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["clerk_id"] == fake_clerk["id"]

    user = await db.get(User, data['id'])
    assert user is not None
    assert user.clerk_id == fake_clerk["id"]

    user_key = get_token_key(auth_headers['Authorization'].split(' ')[-1])
    record = await redis_conn.get(user_key)
    assert record == str(data['id'])


async def test_login_existing_user(
    client: AsyncClient,
    db: AsyncSession,
    redis_conn: Redis,
    fake_user,
    fake_clerk,
    mock_clerk_success
):

    user_created = User(**fake_user(fake_clerk))
    db.add(user_created)
    await db.commit()
    await db.refresh(user_created)

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "clerk_id": user_created.clerk_id,
            "email": user_created.email,
            "name": user_created.name
        },
        headers= {"Authorization": f"Bearer {user_created.clerk_id}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["clerk_id"] == user_created.clerk_id

async def test_invalid_clerk_token(
    client: AsyncClient,
    db: AsyncSession,
    redis_conn: Redis,
    mock_clerk_failure,
    auth_headers
):
    response = await client.post(
        "/api/v1/auth/login",
        headers=auth_headers
    )

    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]

async def test_logout(
    client: AsyncClient,
    db: AsyncSession,
    redis_conn: Redis,
    fake_user,
    fake_clerk,
    mock_clerk_success
):
    user_created = User(**fake_user(fake_clerk))
    db.add(user_created)
    await db.commit()
    await db.refresh(user_created)

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "clerk_id": user_created.clerk_id,
            "email": user_created.email,
            "name": user_created.name
        },
        headers= {"Authorization": f"Bearer {user_created.clerk_id}"}
    )

    assert response.status_code == 200

    response = await client.post(
        "/api/v1/auth/logout",
        headers= {"Authorization": f"Bearer {user_created.clerk_id}"}
    )

    assert response.status_code == 200
