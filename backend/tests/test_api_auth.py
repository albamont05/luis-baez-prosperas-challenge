import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_user(async_client: AsyncClient):
    response = await async_client.post(
        "/register",
        json={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data

@pytest.mark.asyncio
async def test_register_existing_user(async_client: AsyncClient):
    # Registrar la primera vez
    await async_client.post(
        "/register",
        json={"username": "testuser", "password": "testpassword"}
    )
    # Registrar con el mismo nombre
    response = await async_client.post(
        "/register",
        json={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient):
    await async_client.post(
        "/register",
        json={"username": "anotheruser", "password": "securepassword"}
    )
    # Login usando form data (OAuth2PasswordRequestForm requiere urlencoded form data)
    response = await async_client.post(
        "/login",
        data={"username": "anotheruser", "password": "securepassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_failure(async_client: AsyncClient):
    response = await async_client.post(
        "/login",
        data={"username": "nonexistent", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"
