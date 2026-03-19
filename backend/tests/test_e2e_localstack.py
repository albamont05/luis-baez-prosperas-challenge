import os
import uuid
import pytest
import asyncio
import aioboto3
from httpx import AsyncClient
from app.core.config import settings

# Marcador personalizado "localstack" (puede omitirse con pytest -m "not localstack")
pytestmark = pytest.mark.localstack

@pytest.mark.skipif(os.getenv("USE_REAL_ENV", "false").lower() != "true", reason="E2E request USE_REAL_ENV=true")
@pytest.mark.asyncio
async def test_e2e_localstack_and_db_integration(async_client: AsyncClient):
    """
    Test E2E sin mocks:
    - Se registra y loguea (usa la base de datos de Postgres local de docker)
    - Solicita trabajo (envía SQS)
    - SQS -> Worker -> S3 Upload, cambia status a COMPLETED -> BD Real
    - Valida que funcione en armonía interactuando con las piezas reales de LocalStack
    """
    user_suffix = str(uuid.uuid4())[:8]
    username = f"e2e_user_{user_suffix}"
    password = "e2e_password"
    
    # 1. Registrar y obtener JWT
    res_reg = await async_client.post("/register", json={"username": username, "password": password})
    assert res_reg.status_code == 201
    
    res_log = await async_client.post("/login", data={"username": username, "password": password})
    assert res_log.status_code == 200
    token = res_log.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Pre-Vincular configuracion localstack para interactuar con boto3 directamente
    kwargs = {}
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
        
    session = aioboto3.Session(
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key
    )
    
    # (Opcional) Verificamos S3 con head_object subiendo un test object
    async with session.client('s3', **kwargs) as s3:
        test_key = f"e2e_test_{user_suffix}.txt"
        await s3.put_object(Bucket=settings.s3_bucket_name, Key=test_key, Body=b"E2E Integration Test")
        resp = await s3.head_object(Bucket=settings.s3_bucket_name, Key=test_key)
        assert resp["ContentLength"] > 0
    
    # 2. Crear un Job (Este generará un evento a SQS)
    res_job = await async_client.post("/jobs", json={"report_type": "CSV"}, headers=headers)
    assert res_job.status_code == 201
    job_id = res_job.json()["job_id"]
    
    # 3. Esperar que el worker lea LocalStack SQS, procese y suba S3
    max_retries = 15
    job_completed = False
    
    for _ in range(max_retries):
        await asyncio.sleep(1.0)
        res_get = await async_client.get(f"/jobs/{job_id}", headers=headers)
        if res_get.status_code == 200:
            job_data = res_get.json()
            if job_data["status"] == "COMPLETED":
                job_completed = True
                assert job_data["result_url"] is not None
                assert settings.s3_bucket_name in job_data["result_url"]
                break
            elif job_data["status"] == "FAILED":
                pytest.fail("El Worker falló procesando el test de LocalStack E2E real.")
                
    assert job_completed, "El worker no completó el procesamiento vía SQS a Postgres a tiempo."
