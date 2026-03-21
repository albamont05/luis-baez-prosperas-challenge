import json
import logging
import asyncio
from uuid import UUID
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.db import AsyncSessionLocal, init_db
from app.models.job import JobStatus
from app.services.job import update_job_status
from app.services.aws import session as boto_session, get_aws_client_kwargs, upload_file_to_s3
from app.core.circuit_breaker import aws_circuit_breaker, db_circuit_breaker

# Configuración de logging para visibilidad total en Docker
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@db_circuit_breaker
async def _safe_update_status(job_id: UUID, status: JobStatus, result_url: str = None):
    """Encapsula la actualización en DB con Circuit Breaker"""
    async with AsyncSessionLocal() as session:
        return await update_job_status(session, job_id, status, result_url)

async def process_job(job_id_str: str, report_type: str):
    """
    Lógica de procesamiento: Simulación -> S3 -> DB Update
    """
    try:
        job_id = UUID(job_id_str)
    except ValueError:
        logger.error(f"ID de trabajo inválido: {job_id_str}")
        return

    # 1. Marcar como PROCESSING
    try:
        await _safe_update_status(job_id, JobStatus.PROCESSING)
    except Exception as e:
        logger.error(f"Error marcando PROCESSING para {job_id}: {e}")
        return
            
    logger.info(f"Worker procesando trabajo {job_id} ({report_type})...")
    
    try:
        # 2. Simulación de procesamiento (3 segundos)
        await asyncio.sleep(3) 
        
        file_content = f"ID: {job_id}\nType: {report_type}\nStatus: Completed".encode("utf-8")
        file_name = f"{job_id}.{'csv' if report_type == 'CSV' else 'pdf'}"
        content_type = "text/csv" if report_type == "CSV" else "application/pdf"
        
        # 3. Subida a S3 (LocalStack)
        result_url = await upload_file_to_s3(file_content, file_name, content_type)
        
        # 4. Éxito: Marcar como COMPLETED
        await _safe_update_status(job_id, JobStatus.COMPLETED, result_url=result_url)
        logger.info(f"Trabajo {job_id} procesado y subido con éxito.")

    except Exception as e:
        logger.error(f"Error durante el procesamiento del trabajo {job_id}: {e}")
        # Intento de marcar como FAILED si algo sale mal
        try:
            await _safe_update_status(job_id, JobStatus.FAILED)
        except Exception as inner_e:
            logger.error(f"No se pudo marcar como FAILED en DB: {inner_e}")

@aws_circuit_breaker
async def _receive_messages(sqs, queue_url):
    """Polling de mensajes con Circuit Breaker"""
    return await sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=5
    )

@aws_circuit_breaker
async def _delete_message(sqs, queue_url, receipt_handle):
    """Eliminación de mensajes con Circuit Breaker"""
    return await sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)

async def run_worker():
    """Bucle principal con estrategia de resiliencia para LocalStack"""
    logger.info("Iniciando Background Worker...")
    
    # Inicializar tablas si no existen
    await init_db()

    kwargs = get_aws_client_kwargs()
    
    async with boto_session.client('sqs', **kwargs) as sqs:
        queue_url = None
        max_retries = 15
        retry_delay = 3

        # ESTRATEGIA DE REINTENTO: Esperar a que la infraestructura esté lista
        for attempt in range(max_retries):
            try:
                logger.info(f"Intentando conectar a SQS: {settings.sqs_queue_name} (Intento {attempt+1})")
                response = await sqs.get_queue_url(QueueName=settings.sqs_queue_name)
                queue_url = response['QueueUrl']
                logger.info(f"Conexión establecida. URL: {queue_url}")
                break
            except (ClientError, Exception) as e:
                logger.warning(f"Infraestructura AWS no lista aún. Reintentando en {retry_delay}s...")
                await asyncio.sleep(retry_delay)
        
        if not queue_url:
            logger.error("No se pudo conectar a SQS tras los reintentos. El contenedor se detendrá.")
            return

        # Bucle de Polling infinito
        while True:
            try:
                response = await _receive_messages(sqs, queue_url)
                
                messages = response.get('Messages', [])
                if not messages:
                    continue
                    
                for message in messages:
                    receipt_handle = message['ReceiptHandle']
                    try:
                        body = json.loads(message['Body'])
                        job_id = body.get('job_id')
                        report_type = body.get('report_type')
                        
                        if job_id:
                            await process_job(job_id, report_type)
                        
                        # Eliminar mensaje tras procesar
                        await _delete_message(sqs, queue_url, receipt_handle)
                        logger.info(f"Mensaje {job_id} procesado y eliminado.")

                    except json.JSONDecodeError:
                        logger.error("Mensaje malformado recibido. Eliminando...")
                        await _delete_message(sqs, queue_url, receipt_handle)
                        
            except Exception as e:
                if "OPEN" in str(e):
                    logger.warning("Circuit Breaker AWS abierto. Pausando worker 10s...")
                    await asyncio.sleep(10)
                else:
                    logger.error(f"Error inesperado en el bucle: {e}")
                    await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker detenido manualmente.")