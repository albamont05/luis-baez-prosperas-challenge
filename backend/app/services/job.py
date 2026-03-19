import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.job import Job, JobStatus, JobType
from app.core.circuit_breaker import db_circuit_breaker
from app.services.aws import send_job_request_to_sqs

@db_circuit_breaker
async def create_job(session: AsyncSession, report_type: JobType, user_id: uuid.UUID) -> Job:
    """
    Registra el trabajo en la base de datos con estado PENDING.
    """
    new_job = Job(report_type=report_type, user_id=user_id, status=JobStatus.PENDING)
    session.add(new_job)
    await session.commit()
    await session.refresh(new_job)
    return new_job

async def queue_job_generation(job_id: uuid.UUID, report_type: JobType):
    """
    Lógica de orquestación que llama al servicio SQS.
    El servicio AWS SQS ya incluye su propio Circuit Breaker.
    """
    await send_job_request_to_sqs(str(job_id), report_type.value)

@db_circuit_breaker
async def get_job_by_id(session: AsyncSession, job_id: uuid.UUID, user_id: uuid.UUID = None) -> Job:
    """
    Busca un trabajo en la BD por su ID.
    Opcionalmente valida el user_id.
    """
    stmt = select(Job).where(Job.job_id == job_id)
    if user_id:
        stmt = stmt.where(Job.user_id == user_id)
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    return job

@db_circuit_breaker
async def get_jobs_for_user(session: AsyncSession, user_id: uuid.UUID, skip: int = 0, limit: int = 20):
    """
    Lista los trabajos de un usuario con paginación.
    """
    stmt = select(Job).where(Job.user_id == user_id).offset(skip).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()

@db_circuit_breaker
async def update_job_status(
    session: AsyncSession, 
    job_id: uuid.UUID, 
    status: JobStatus, 
    result_url: str = None
) -> Job:
    """
    Actualiza el estado de un trabajo.
    No requiere user_id porque se usa en el worker que procesa por job_id.
    """
    job = await get_job_by_id(session, job_id)
    if not job:
        raise ValueError(f"Trabajo {job_id} no encontrado")
        
    job.status = status
    if result_url:
        job.result_url = result_url
        
    await session.commit()
    await session.refresh(job)
    return job
