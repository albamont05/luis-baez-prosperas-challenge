#!/bin/bash
echo "########### Creando infraestructura local ###########"

# Crear SQS
awslocal sqs create-queue --queue-name reports-queue

# Crear S3
awslocal s3 mb s3://prosperas-reports-bucket

echo "########### Configuración completada ###########"