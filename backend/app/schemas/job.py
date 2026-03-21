from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.job import JobType, JobStatus

class JobCreate(BaseModel):
    report_type: JobType

    model_config = ConfigDict(from_attributes=True)

class JobResponse(BaseModel):
    job_id: UUID
    user_id: UUID
    report_type: JobType
    status: JobStatus
    result_url: Optional[str] = None
    # Pre-signed URL generada dinámicamente — no persiste en la BD
    download_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
