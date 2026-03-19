import pytest
import uuid
from unittest.mock import patch, AsyncMock
from sqlalchemy.future import select

from app.worker.main import process_job
from app.models.job import Job, JobStatus, JobType
from app.models.user import User
from tests.conftest import TestingSessionLocal
from app.core.security import get_password_hash

# Fixture to mock AWS S3 upload
@pytest.fixture
def mock_upload_s3():
    with patch("app.worker.main.upload_file_to_s3", new_callable=AsyncMock) as mock:
        mock.return_value = "https://s3.amazonaws.com/test-bucket/result.csv"
        yield mock

# Fixture to patch the worker's DB connection to use the in-memory one
@pytest.fixture(autouse=True)
def patch_worker_db():
    with patch("app.worker.main.AsyncSessionLocal", new=TestingSessionLocal):
        yield

@pytest.mark.asyncio
async def test_process_job_success(mock_upload_s3):
    # Setup test data: a user and a pending job in the DB
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    
    async with TestingSessionLocal() as session:
        user = User(id=user_id, username="worker_test", hashed_password=get_password_hash("pass"))
        session.add(user)
        job = Job(job_id=job_id, user_id=user_id, report_type=JobType.CSV, status=JobStatus.PENDING)
        session.add(job)
        await session.commit()
    
    # Exec logic
    await process_job(str(job_id), "CSV")
    
    # Assert side effects
    mock_upload_s3.assert_called_once()
    
    # Assert DB changes
    async with TestingSessionLocal() as session:
        stmt = select(Job).where(Job.job_id == job_id)
        result = await session.execute(stmt)
        processed_job = result.scalar_one()
        
        assert processed_job.status == JobStatus.COMPLETED
        assert processed_job.result_url == "https://s3.amazonaws.com/test-bucket/result.csv"

@pytest.mark.asyncio
async def test_process_job_failure_s3():
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    
    async with TestingSessionLocal() as session:
        user = User(id=user_id, username="worker_fail", hashed_password=get_password_hash("pass"))
        session.add(user)
        job = Job(job_id=job_id, user_id=user_id, report_type=JobType.PDF, status=JobStatus.PENDING)
        session.add(job)
        await session.commit()
    
    # Mock upload to raise an exception
    with patch("app.worker.main.upload_file_to_s3", new_callable=AsyncMock) as mock:
        mock.side_effect = Exception("S3 upload failed")
        await process_job(str(job_id), "PDF")
    
    async with TestingSessionLocal() as session:
        stmt = select(Job).where(Job.job_id == job_id)
        result = await session.execute(stmt)
        failed_job = result.scalar_one()
        
        assert failed_job.status == JobStatus.FAILED
        assert failed_job.result_url is None
