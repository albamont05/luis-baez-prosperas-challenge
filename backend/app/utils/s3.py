import logging
from app.core.config import settings
from app.models.job import JobStatus
from app.schemas.job import JobResponse
from app.services.aws import get_presigned_url

logger = logging.getLogger(__name__)

def extract_s3_key(result_url: str) -> str | None:
    """
    Extrae la clave (key) de S3 a partir de la result_url almacenada.
    Lógica robusta: intenta encontrar el nombre del archivo tras el bucket
    o simplemente toma el último componente de la ruta.
    """
    if not result_url:
        return None
        
    try:
        # 1. Quitar query-string si lo hubiera
        path = result_url.split("?")[0]
        
        # 2. Intentar por marcador de bucket (S3 Path Style o LocalStack)
        bucket = settings.s3_bucket_name
        marker = f"/{bucket}/"
        if marker in path:
            return path.split(marker, 1)[1]
            
        # 3. Fallback: El último componente de la URL es usualmente el Key 
        # (funciona para Virtual Hosted Style 'bucket.s3.amazonaws.com/key')
        return path.split("/")[-1]
    except Exception as e:
        logger.warning(f"Error extrayendo S3 key de {result_url}: {e}")
        return None

async def enrich_job_with_download_url(job: JobResponse) -> JobResponse:
    """
    Si el job está COMPLETADO y tiene result_url, genera una pre-signed URL
    y la adjunta como download_url (campo computado).
    """
    if job.status == JobStatus.COMPLETED and job.result_url:
        key = extract_s3_key(job.result_url)
        if key:
            try:
                url = await get_presigned_url(settings.s3_bucket_name, key)
                return job.model_copy(update={"download_url": url})
            except Exception as exc:
                logger.warning("No se pudo generar pre-signed URL para %s: %s", key, exc)
    return job
