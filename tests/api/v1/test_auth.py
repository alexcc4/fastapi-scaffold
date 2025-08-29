from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from tests.conftest import create_test_user, login_test_user


async def test_oauth2_token_login(client: AsyncClient, db: AsyncSession):
    user, auth_user = await create_test_user(db, auth_id="testuser", password="test123")
    
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "testuser", "password": "test123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["access_token"] != ""


async def test_oauth2_token_login_invalid_credentials(client: AsyncClient, db: AsyncSession):
    await create_test_user(db, auth_id="testuser", password="test123")
    
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "testuser", "password": "wrongpassword"}
    )
    
    assert response.status_code == 401


async def test_custom_login(client: AsyncClient, db: AsyncSession):
    user, auth_user = await create_test_user(db, auth_id="testuser", password="test123")
    
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "auth_id": "testuser",
            "auth_type": 1,
            "credential": "test123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "user" in data
    assert data["user"]["id"] == user.id
    assert data["user"]["name"] == "testuser"


async def test_custom_login_invalid_credentials(client: AsyncClient, db: AsyncSession):
    await create_test_user(db, auth_id="testuser", password="test123")
    
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "auth_id": "testuser", 
            "auth_type": 1,
            "credential": "wrongpassword"
        }
    )
    
    assert response.status_code == 401


async def test_get_current_user_me(client: AsyncClient, db: AsyncSession):
    user, auth_user = await create_test_user(db, auth_id="testuser", password="test123")
    token = await login_test_user(client, auth_id="testuser", password="test123")
    
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["name"] == "testuser"
    assert data["status"] == 1
    assert "created_at" in data


async def test_get_current_user_without_token(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_get_current_user_with_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


async def test_logout(client: AsyncClient, db: AsyncSession, redis_client: Redis):
    user, auth_user = await create_test_user(db, auth_id="testuser", password="test123")
    token = await login_test_user(client, auth_id="testuser", password="test123")
    
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    
    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Logged out successfully"
    
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


async def test_logout_without_token(client: AsyncClient):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 401


async def test_logout_with_invalid_token(client: AsyncClient):
    """test logout with invalid token"""
    response = await client.post(
        "/api/v1/auth/logout", 
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
