#!/bin/bash
set -e # Detiene el script si algo falla catastróficamente

echo "########### Iniciando Aprovisionamiento de AWS Local ###########"

# 1. Crear Cola SQS (Solo si no existe)
if ! awslocal sqs get_queue_url --queue-name reports-queue >/dev/null 2>&1; then
    echo "Creando cola SQS: reports-queue..."
    awslocal sqs create-queue --queue-name reports-queue
else
    echo "La cola SQS 'reports-queue' ya existe. Omitiendo."
fi

# 2. Crear Bucket S3 (Solo si no existe)
if ! awslocal s3api head-bucket --bucket prosperas-reports-bucket >/dev/null 2>&1; then
    echo "Creando bucket S3: prosperas-reports-bucket..."
    awslocal s3 mb s3://prosperas-reports-bucket
    
    # 3. Configurar CORS (Vital para que el Dashboard de React no falle)
    echo "Configurando políticas CORS para el bucket..."
    cat <<EOF > /tmp/cors-config.json
{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
      "AllowedHeaders": ["*"],
      "ExposeHeaders": ["ETag"]
    }
  ]
}
EOF
    awslocal s3api put-bucket-cors --bucket prosperas-reports-bucket --cors-configuration file:///tmp/cors-config.json
else
    echo "El bucket 'prosperas-reports-bucket' ya existe. Omitiendo."
fi

echo "########### Infraestructura lista y persistente ###########"