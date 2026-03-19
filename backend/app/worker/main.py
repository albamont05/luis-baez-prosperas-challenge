import json
import logging
import asyncio
from uuid import UUID

from app.core.config import settings
from app.core.db import AsyncSessionLocal, init_db
from app.models.job import JobStatus
from app.services.job import update_job_status
from app.services.aws import session as boto_session, get_aws_client_kwargs, upload_file_to_s3
from app.core.circuit_breaker import aws_circuit_breaker, db_circuit_breaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@db_circuit_breaker
async def _safe_update_status(job_id: UUID, status: JobStatus, result_url: str = None):
    """Encapsula la creación de la sesión y la actualización en el DB Circuit Breaker"""
    async with AsyncSessionLocal() as session:
        return await update_job_status(session, job_id, status, result_url)

async def process_job(job_id_str: str, report_type: str):
    """
    Genera el trabajo, lo sube a S3 y actualiza la base de datos a COMPLETED/FAILED.
    """
    job_id = UUID(job_id_str)
    
    # 1. Marcar como PROCESSING en DB
    try:
        await _safe_update_status(job_id, JobStatus.PROCESSING)
    except Exception as e:
        logger.error(f"Error marcando PROCESSING para {job_id}: {e}")
        return # Abortamos procesamiento si la BD falla
            
    # 2. Simular generación del reporte/job
    logger.info(f"Worker procesando trabajo {job_id} de tipo {report_type}...")
    await asyncio.sleep(3) # Simulación de procesamiento pesado
    
    file_content = f"ID: {job_id}\nType: {report_type}\nStatus: Completed".encode("utf-8")
    file_name = f"{job_id}.{'csv' if report_type == 'CSV' else 'pdf'}"
    content_type = "text/csv" if report_type == "CSV" else "application/pdf"
    
    try:
        # 3. Subir a S3
        result_url = await upload_file_to_s3(file_content, file_name, content_type)
        
        # 4. Marcar como COMPLETED en DB
        await _safe_update_status(job_id, JobStatus.COMPLETED, result_url=result_url)
            
        logger.info(f"Trabajo {job_id} procesado con éxito.")
    except Exception as e:
        logger.error(f"Error generando/subiendo trabajo {job_id}: {e}")
        # Si falló, intentar marcar como FAILED
        try:
            await _safe_update_status(job_id, JobStatus.FAILED)
        except Exception as inner_e:
            logger.error(f"Error marcando FAILED para {job_id}: {inner_e}")

@aws_circuit_breaker
async def _receive_messages(sqs, queue_url):
    return await sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=5 # Long polling
    )

@aws_circuit_breaker
async def _delete_message(sqs, queue_url, receipt_handle):
    return await sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)

async def run_worker():
    """Bucle principal del worker independiente."""
    logger.info("Iniciando Background Worker para generación de trabajos (Jobs)...")
    
    # Asegurarse de que la BD existe
    await init_db()

    kwargs = get_aws_client_kwargs()
    # Context manager externo: El cliente SQS vive durante todo el bucle
    async with boto_session.client('sqs', **kwargs) as sqs:
        # Optimización: Obtener URL de la cola UNA sola vez
        try:
            queue_url_response = await sqs.get_queue_url(QueueName=settings.sqs_queue_name)
            queue_url = queue_url_response['QueueUrl']
            logger.info(f"SQS Queue URL configurada: {queue_url}")
        except Exception as e:
            logger.error(f"Fallo crítico al obtener QueueUrl: {e}")
            return

        while True:
            try:
                response = await _receive_messages(sqs, queue_url)
                
                messages = response.get('Messages', [])
                if not messages:
                    # logger.debug("No hay mensajes en SQS.")
                    continue
                    
                for message in messages:
                    receipt_handle = message['ReceiptHandle']
                    body = json.loads(message['Body'])
                    
                    job_id = body.get('job_id')
                    report_type = body.get('report_type')
                    
                    if not job_id:
                        logger.warning("Mensaje sin job_id encontrado, saltando...")
                        try:
                            await _delete_message(sqs, queue_url, receipt_handle)
                        except Exception:
                            pass
                        continue
                        
                    # Llamar al proceso
                    await process_job(job_id, report_type)
                    
                    # Eliminar mensaje tras procesar con circuit breaker 
                    try:
                        await _delete_message(sqs, queue_url, receipt_handle)
                        logger.info(f"Mensaje eliminado de la cola SQS satisfactoriamente.")
                    except Exception as e:
                        logger.error(f"No se pudo eliminar mensaje de SQS preventivamente: {e}")
                        
            except Exception as e:
                if "OPEN" in str(e):
                    logger.warning("Circuit Breaker activo (OPEN). Esperando antes de continuar el polling...")
                else:
                    logger.error(f"Error en bucle de polling SQS: {e}")
                
                await asyncio.sleep(5) # Delay de recuperación

if __name__ == "__main__":
    asyncio.run(run_worker())
