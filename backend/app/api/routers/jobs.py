from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
import logging

from app.core.db import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.job import JobStatus
from app.models.user import User
from app.schemas.job import JobCreate, JobResponse
from app.services.job import create_job, queue_job_generation, get_job_by_id, get_jobs_for_user
from app.utils.s3 import enrich_job_with_download_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])




@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def request_job(
    request: JobCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Solicita la generación de un nuevo trabajo."""
    new_job = await create_job(session, request.report_type, current_user.id)
    await queue_job_generation(new_job.job_id, request.report_type)
    return new_job


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consulta el estado de un trabajo específico."""
    job = await get_job_by_id(session, job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not accessible")

    response = JobResponse.model_validate(job)
    return await enrich_job_with_download_url(response)


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=20),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene los trabajos del usuario paginados (mín. 20)."""
    jobs = await get_jobs_for_user(session, current_user.id, skip, limit)
    responses = [JobResponse.model_validate(j) for j in jobs]
    # Enriquecer en paralelo — no bloqueamos el event loop
    import asyncio
    return await asyncio.gather(*[enrich_job_with_download_url(r) for r in responses])
