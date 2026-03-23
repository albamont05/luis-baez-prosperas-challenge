# Prosperas Reports Challenge - Sistema de Reportes Asíncronos

Este repositorio contiene una plataforma escalable y resiliente para la generación de reportes pesados, diseñada bajo una arquitectura orientada a eventos y desplegada íntegramente en AWS.

## 1. Arquitectura de Infraestructura

El sistema opera mediante una distribución de servicios desacoplados para garantizar alta disponibilidad y una experiencia de usuario fluida:

*   **Frontend (Puerto 80):** SPA construida con **React + Vite**, desplegada en un contenedor Nginx. Se comunica con la API vía REST y WebSockets.
*   **Backend API (Puerto 8000):** Servicio robusto con **FastAPI** que gestiona la autenticación, creación de tareas y orquestación de notificaciones.
*   **Mensajería (Amazon SQS):** Actúa como buffer asíncrono. La API encola solicitudes de reporte en la cola `reports-queue`, permitiendo respuestas inmediatas al cliente.
*   **Workers (2x Réplicas):** Consumidores independientes que realizan el procesamiento pesado (generación de PDF/CSV) y suben el resultado final a Amazon S3.
*   **Almacenamiento (Amazon S3):** Persistencia de archivos generados con acceso seguro mediante **Pre-signed URLs** temporales.
*   **Base de Datos (Amazon RDS):** Postgres gestionado para la persistencia de usuarios y estados de procesamiento de los trabajos.

---

## 2. CI/CD y Pipeline de Despliegue

La automatización se gestiona mediante **GitHub Actions** (`.github/workflows/main.yml`), implementando un flujo continuo de entrega:

1.  **Build & Tagging:** Construcción de imágenes Docker multi-etapa para optimizar el tamaño.
2.  **Inyección de Variables:** Durante el build del Frontend, se inyecta la variable `VITE_API_BASE_URL` (IP pública de la instancia EC2) para asegurar la conectividad en el entorno de producción.
3.  **Amazon ECR:** Las imágenes se taguean como `latest` y se suben al registro privado de Amazon ECR.
4.  **Automatic Deploy:** El pipeline se conecta vía SSH a la instancia **EC2**, realiza un `pull` de las nuevas imágenes y reinicia los servicios usando **Docker Compose**.

---

## 3. Estrategias de Resiliencia

El sistema está diseñado para fallar de manera segura y controlada (**Fail-Fast**):

*   **Circuit Breakers:** Implementados en las conexiones críticas hacia RDS y AWS (SQS/S3). Si un servicio externo falla repetidamente, el circuito se abre para proteger la integridad del backend y notificar al frontend.
*   **AWS Connectivity Check:** Durante el arranque del backend, se verifica la existencia y conectividad de los recursos de AWS (Bucket y SQS), deteniendo el proceso si la infraestructura no está lista.
*   **Reintentos en Workers:** Los Workers implementan reintentos exponenciales para manejar latencias temporales en la nube.

---

## 4. Guía de Variables de Entorno (.env)

Para el despliegue en producción, se requiere un archivo `.env` con la siguiente configuración. 

> [!IMPORTANT]
> Para la configuración de SQS, se debe proporcionar únicamente el **nombre de la cola** (`SQS_QUEUE_NAME`) y no la URL completa, para garantizar la compatibilidad con la resolución automática del SDK de AWS.

| Variable | Descripción |
| :--- | :--- |
| `APP_ENV` | Entorno de ejecución (`production`). |
| `DATABASE_URL` | URI de conexión a RDS (`postgresql+asyncpg://...`). |
| `AWS_REGION` | Región de AWS (ej: `us-east-1`). |
| `AWS_ACCESS_KEY_ID` | Credenciales de IAM con permisos en S3/SQS. |
| `AWS_SECRET_ACCESS_KEY` | Credenciales de IAM con permisos en S3/SQS. |
| `SQS_QUEUE_NAME` | Nombre de la cola (ej: `reports-queue`). |
| `S3_BUCKET_NAME` | Nombre del bucket (ej: `prosperas-reports-bucket`). |
| `SECRET_KEY` | Clave para el cifrado de JWT. |

---

## 5. Ejecución y Escalado

### Despliegue en Producción
Una vez configuradas las variables de entorno en la instancia, ejecute:
```bash
docker-compose up -d
```

### Escalado de Workers
Si detecta un cuello de botella en el procesamiento, puede escalar el número de réplicas dinámicamente:
```bash
docker-compose up -d --scale worker=5
```

---

*Desarrollado con enfoque en mantenibilidad, escalabilidad y excelencia técnica.*
