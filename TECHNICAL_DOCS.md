# Documentación Técnica - Prosperas Reports Challenge

Este documento detalla la arquitectura, decisiones de diseño y procedimientos operativos del sistema de generación de reportes de Prosperas. Está diseñado para ser la referencia principal para ingenieros de mantenimiento y nuevos desarrolladores.

## 1. Diagrama de Arquitectura

El sistema utiliza una **Arquitectura Orientada a Eventos (EDA)** para garantizar que la generación de reportes pesados no impacte la latitud de la API principal.

```mermaid
graph TD
    subgraph "Capa de Cliente"
        Vite["Frontend (Vite/React)"]
    end

    subgraph "Backend (FastAPI)"
        API["API Rest"]
        WS["WebSocket Server (Notificaciones)"]
        CB["Circuit Breaker (Resiliencia)"]
    end

    subgraph "Mensajería (AWS SQS)"
        SQS["reports-queue"]
    end

    subgraph "Procesamiento (Workers)"
        Worker["Concurrent Workers (2x Replicas)"]
    end

    subgraph "Almacenamiento y Datos"
        S3["Amazon S3 (Buckets Privados)"]
        RDS["Amazon RDS (PostgreSQL)"]
    end

    %% Flujos de Datos
    Vite <-->|HTTP/JSON| API
    Vite <-->|WebSockets (Push)| WS
    API -->|1. Registrar Trabajo| RDS
    API -->|2. Encolar Tarea| SQS
    Worker -->|3. Long Polling| SQS
    Worker -->|4. Actualizar Estado| RDS
    Worker -->|5. Subir Reporte| S3
    WS -.->|Consultar Cambio de Estado| RDS
    API -.->|Generar Pre-signed URL| S3
    CB -.->|Protección| RDS
    CB -.->|Protección| SQS
```

---

## 2. Infraestructura y Servicios AWS

| Servicio | Función en el Proyecto | Justificación Técnica |
| :--- | :--- | :--- |
| **Amazon SQS** | Cola de Mensajería | Desacopla la API del procesamiento. Garantiza la persistencia de tareas ante fallos del Worker y gestiona picos de carga mediante escalado horizontal. |
| **Amazon S3** | Almacenamiento de Objetos | Almacena los reportes finales (CSV/PDF) de forma segura. Se utiliza para generar **Pre-signed URLs** de 10 minutos, evitando la exposición pública de datos sensibles. |
| **Amazon RDS** | Base de Datos Relacional | Almacena el estado de los trabajos (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`) y la información de usuarios con integridad referencial total. |
| **Amazon EC2 / Red** | Hosting de Contenedores | Proporciona control total sobre la pila de red y WebSockets. Se eligió sobre AWS App Runner para evitar limitaciones de cuota y permitir una orquestación granular con Docker Compose. |

---

## 3. Decisiones de Diseño y Trade-offs

### 3.1 WebSockets sobre Polling (B3)
*   **Decisión:** Se utiliza WebSockets para notificar cambios de estado en tiempo real. 
*   **Razón:** El polling tradicional desde el cliente (Vite) satura innecesariamente el servidor con peticiones HTTP 200/304. WebSockets reduce el tráfico de red y mejora drásticamente la percepción de velocidad del usuario.
*   **Implementación:** El backend realiza un polling interno a la base de datos (cada 3s) y emite un evento solo si detecta un cambio de estado en los trabajos del usuario conectado.

### 3.2 Patrón Circuit Breaker (B2)
*   **Decisión:** Implementado un Circuit Breaker en `backend/app/core/circuit_breaker.py`.
*   **Razón:** Evita el "fallo en cascada". Si RDS o AWS/LocalStack fallan consecutivamente (threshold=3), el circuito se abre por 15 segundos, retornando un error `503 Service Unavailable` inmediatamente en lugar de dejar conexiones colgadas.

### 3.3 Arquitectura de Contenedores (EC2 vs Serverless)
*   **Decisión:** Despliegue en EC2 con Docker Compose.
*   **Trade-off:** Aunque Fargate/App Runner son más "manejables", las restricciones de cuota y presupuesto en el entorno de evaluación dictaron una infraestructura con mayor visibilidad y control de costos fijos.

---

## 4. Guía de Setup Local (LocalStack)

Para levantar el entorno de desarrollo desde cero, siga estos pasos:

1.  **Requisitos:** Docker y Docker Compose instalados.
2.  **Iniciar Docker:**
    ```bash
    docker compose up -d
    ```
3.  **Aprovisionamiento AWS:** El contenedor de LocalStack utiliza el script `local/init-aws.sh` automáticamente para:
    *   Crear la cola SQS `reports-queue`.
    *   Crear el bucket S3 `prosperas-reports-bucket`.
    *   Configurar políticas **CORS** para permitir descargas directas desde el navegador.

---

## 5. Guía de Despliegue (CI/CD)

El pipeline está automatizado mediante **GitHub Actions** (`.github/workflows/main.yml`).

*   **Step 1: Build & Tag:** Escanea y construye las imágenes de Docker para el `backend` y `frontend`.
*   **Step 2: Push a ECR:** Autentica con AWS y sube las imágenes a Amazon Elastic Container Registry (ECR).
*   **Step 3: Deploy a EC2 (Estrategia):** Las instancias de EC2 están configuradas para hacer un `docker compose pull` y `up` al detectar nuevas imágenes con el tag `latest`, garantizando un tiempo de inactividad mínimo.

---

## 6. Diccionario de Variables de Entorno

| Variable | Propósito Funcional |
| :--- | :--- |
| `AWS_ENDPOINT_URL` | URL de LocalStack (`http://localhost:4566`) o vacío en producción para usar AWS nativo. |
| `DATABASE_URL` | String de conexión asíncrono para PostgreSQL (`postgresql+asyncpg://...`). |
| `SQS_QUEUE_NAME` | Identificador de la cola de mensajes (Default: `reports-queue`). |
| `S3_BUCKET_NAME` | Nombre del bucket para almacenamiento de archivos (Default: `prosperas-reports-bucket`). |
| `SECRET_KEY` | Clave para la firma de tokens JWT. |

---

## 7. Documentación de Testing

### Suites de Pruebas
1.  **Unitarios:** Ubicados en `/tests`. Utilizan **Mocks** (vía `unittest.mock`) para simular respuestas de S3 y SQS, permitiendo probar la lógica de negocio y autenticación sin dependencias externas.
2.  **Integración / E2E:** `test_e2e_localstack.py`. Estas pruebas requieren el entorno de Docker levantado, ya que interactúan con las instancias reales de LocalStack y Postgres para validar el flujo "End-to-End".

### Comandos de Ejecución
```bash
# Ejecutar todos los tests
pytest

# Ejecutar solo tests unitarios (omitiendo LocalStack)
pytest -m "not localstack"

# Ejecutar con salida detallada
pytest -v
```

---
*Documento generado bajo los estándares de Ingeniería Senior de Prosperas.*
