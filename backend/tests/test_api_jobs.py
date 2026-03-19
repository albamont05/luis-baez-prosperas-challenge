import pytest
from httpx import AsyncClient
from unittest.mock import patch

async def get_token(client, username, password):
    await client.post("/register", json={"username": username, "password": password})
    res = await client.post("/login", data={"username": username, "password": password})
    return res.json()["access_token"]

@pytest.fixture
def mock_sqs():
    with patch("app.api.routers.jobs.queue_job_generation") as mock:
        yield mock

@pytest.mark.asyncio
async def test_create_job(async_client: AsyncClient, mock_sqs):
    token = await get_token(async_client, "user_create", "pass123")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await async_client.post(
        "/jobs",
        json={"report_type": "PDF"},
        headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["report_type"] == "PDF"
    assert data["status"] == "PENDING"
    assert "job_id" in data
    mock_sqs.assert_called_once()

@pytest.mark.asyncio
async def test_get_job_detail(async_client: AsyncClient, mock_sqs):
    token = await get_token(async_client, "user_detail", "pass123")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Crear
    create_res = await async_client.post("/jobs", json={"report_type": "CSV"}, headers=headers)
    job_id = create_res.json()["job_id"]
    
    # Detalle
    detail_res = await async_client.get(f"/jobs/{job_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["job_id"] == job_id

@pytest.mark.asyncio
async def test_list_jobs_pagination(async_client: AsyncClient, mock_sqs):
    token = await get_token(async_client, "user_list", "pass123")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Crear 3 jobs
    for _ in range(3):
        await async_client.post("/jobs", json={"report_type": "CSV"}, headers=headers)
        
    # Validamos que un límite menor a 20 levanta error 422
    response = await async_client.get("/jobs?limit=2", headers=headers)
    assert response.status_code == 422 
    
    response_default = await async_client.get("/jobs", headers=headers)
    assert response_default.status_code == 200
    assert len(response_default.json()) == 3

@pytest.mark.asyncio
async def test_security_isolation(async_client: AsyncClient, mock_sqs):
    token_a = await get_token(async_client, "user_a", "pass123")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    token_b = await get_token(async_client, "user_b", "pass123")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # User A crea
    res_a = await async_client.post("/jobs", json={"report_type": "CSV"}, headers=headers_a)
    job_id_a = res_a.json()["job_id"]
    
    # User B intenta ver el trabajo de User A
    res_b = await async_client.get(f"/jobs/{job_id_a}", headers=headers_b)
    assert res_b.status_code == 404
