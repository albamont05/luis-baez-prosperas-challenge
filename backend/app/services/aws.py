import json
import logging
import aioboto3
from app.core.config import settings
from app.core.circuit_breaker import aws_circuit_breaker

logger = logging.getLogger(__name__)

# Reutilizar una sola sesión de aioboto3 es buena práctica
session = aioboto3.Session(
    region_name=settings.aws_region,
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key
)

def get_aws_client_kwargs():
    """Configuración básica de cliente Boto3. Usa Localstack si se define endpoint."""
    kwargs = {}
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
    return kwargs

@aws_circuit_breaker
async def send_job_request_to_sqs(job_id: str, report_type: str):
    """
    Envía un mensaje a SQS con el ID del reporte y el tipo.
    """
    kwargs = get_aws_client_kwargs()
    async with session.client('sqs', **kwargs) as sqs:
        # Obtener URL de la cola primero
        queue_url_response = await sqs.get_queue_url(QueueName=settings.sqs_queue_name)
        queue_url = queue_url_response['QueueUrl']
        
        message_body = json.dumps({
            "job_id": job_id,
            "report_type": report_type
        })
        
        response = await sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=message_body
        )
        logger.info(f"Mensaje enviado a SQS para reporte {job_id}. MessageId: {response.get('MessageId')}")
        return response

@aws_circuit_breaker
async def upload_file_to_s3(file_content: bytes, file_name: str, content_type: str) -> str:
    """
    Sube el archivo final a S3 y retorna la URL del mismo.
    """
    kwargs = get_aws_client_kwargs()
    async with session.client('s3', **kwargs) as s3:
        await s3.put_object(
            Bucket=settings.s3_bucket_name,
            Key=file_name,
            Body=file_content,
            ContentType=content_type
        )
        
        # En producción sería una URL más estandarizada de S3
        if settings.aws_endpoint_url:
            s3_url = f"{settings.aws_endpoint_url}/{settings.s3_bucket_name}/{file_name}"
        else:
            s3_url = f"https://{settings.s3_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{file_name}"
        
        logger.info(f"Archivo subido a S3: {s3_url}")
        return s3_url

async def verify_aws_connectivity():
    """
    Verifica la conectividad con SQS y S3, levantando excepción
    si los servicios AWS/LocalStack no están disponibles. (Fail-Fast)
    """
    kwargs = get_aws_client_kwargs()
    try:
        # Verificar conexión con SQS interactuando con la cola
        async with session.client('sqs', **kwargs) as sqs:
            await sqs.get_queue_url(QueueName=settings.sqs_queue_name)
            logger.info("Colas SQS conectadas exitosamente.")
            
        # Verificar conexión con S3
        async with session.client('s3', **kwargs) as s3:
            await s3.head_bucket(Bucket=settings.s3_bucket_name)
            logger.info("Bucket S3 conectado exitosamente.")
            
    except Exception as e:
        logger.error(f"Falla crítica: No se pudo conectar a los servicios de AWS: {e}")
        raise RuntimeError(f"AWS Connectivity Check Failed: {e}")
