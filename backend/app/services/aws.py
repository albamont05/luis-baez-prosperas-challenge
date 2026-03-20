import json
import logging
import aioboto3
from botocore.exceptions import ClientError
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
    Verifica la conexión con AWS/LocalStack y asegura que los recursos existan.
    Si el bucket o la cola no existen, intenta crearlos (Resiliencia).
    """
    session = aioboto3.Session(
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region
    )
    
    kwargs = {"endpoint_url": settings.aws_endpoint_url} if settings.aws_endpoint_url else {}

    try:
        # 1. Verificar/Crear S3 Bucket
        async with session.client("s3", **kwargs) as s3:
            try:
                await s3.head_bucket(Bucket=settings.s3_bucket_name)
                logger.info(f"✅ Bucket S3 verificado: {settings.s3_bucket_name}")
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code")
                if error_code == "404":
                    logger.info(f"⚠️ Bucket {settings.s3_bucket_name} no encontrado. Creando...")
                    await s3.create_bucket(Bucket=settings.s3_bucket_name)
                    logger.info(f"✅ Bucket {settings.s3_bucket_name} creado exitosamente.")
                else:
                    raise e

        # 2. Verificar/Crear SQS Queue
        async with session.client("sqs", **kwargs) as sqs:
            try:
                await sqs.get_queue_url(QueueName=settings.sqs_queue_name)
                logger.info(f"✅ Cola SQS verificada: {settings.sqs_queue_name}")
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code")
                # LocalStack a veces devuelve NonExistentQueue
                if error_code in ["AWS.SimpleQueueService.NonExistentQueue", "404"]:
                    logger.info(f"⚠️ Cola {settings.sqs_queue_name} no encontrada. Creando...")
                    await sqs.create_queue(QueueName=settings.sqs_queue_name)
                    logger.info(f"✅ Cola {settings.sqs_queue_name} creada exitosamente.")
                else:
                    raise e

        logger.info("🚀 Infraestructura de mensajería y almacenamiento lista.")
        
    except Exception as e:
        logger.error(f"❌ Falla crítica de infraestructura AWS: {str(e)}")
        # Elevamos el error para que el Lifespan de FastAPI detenga el inicio (Fail-Fast)
        raise RuntimeError(f"AWS Connectivity Check Failed: {e}")