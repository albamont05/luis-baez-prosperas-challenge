# Skills & Context: Prosperas Reports Challenge

Este documento es la **Única Fuente de Verdad (Single Source of Truth - SSoT)** para la transferencia de contexto técnico y el mantenimiento del sistema. Está diseñado para que cualquier desarrollador o agente de IA pueda operar y extender el sistema con una comprensión completa de su arquitectura y operación.

---

## 0. Contexto de Negocio
El sistema resuelve el problema del **procesamiento de tareas de larga duración** en aplicaciones web. Generar reportes pesados (PDF/CSV) de forma síncrona bloquearía los hilos de la API y degradaría la experiencia del usuario (UX). 

Este proyecto implementa una solución asíncrona donde:
1. El usuario solicita un reporte y recibe un `job_id` inmediato.
2. El trabajo se delega a un **Worker** independiente vía colas de mensajería.
3. El usuario recibe actualizaciones de estado en tiempo real vía **WebSockets** sin necesidad de refrescar la página o realizar polling manual.

---

## 1. Mapa del Repositorio
```text
/backend
  /app
    /api       # Routers de FastAPI: /auth (Seguridad), /jobs (Reportes), /ws (WebSockets).
    /core      # El "corazón": config.py, motor de base de datos (db.py) y circuit_breaker.py.
    /models    # Definiciones de tablas SQLAlchemy (User, Job).
    /schemas   # Modelos Pydantic para validación de entrada/salida de la API.
    /services  # Lógica de dominio: aws.py (SQS/S3), job.py (CRUD), notifier.py (WS Manager).
    /worker    # Consumidor asíncrono que procesa mensajes de SQS y genera el archivo final.
    /utils     # Funciones auxiliares (ej. firmas temporales de S3).
/frontend      # Dashboard en Vite + React. Gestiona estados locales y conexión WS.
/local         # Infraestructura: docker-compose.yml y scripts de LocalStack (init-aws.sh).
/.github       # Automatización: CI/CD para construcción y empuje de imágenes a Amazon ECR.
```

---

## 2. Arquitectura y Estrategia de Resiliencia

### Patrón Circuit Breaker (Resiliencia B2)
Implementado en `backend/app/core/circuit_breaker.py` para proteger al sistema de fallos en cascada.
*   **Threshold:** 3 fallos consecutivos.
*   **Timeout de Recuperación:** 15 segundos.
*   **Comportamiento:** Si RDS o SQS fallan, la API retorna `503 Service Unavailable` inmediatamente, permitiendo que el Frontend muestre un mensaje de "Mantenimiento" en lugar de quedar en espera eterna.

---

## 3. Guía de Comandos Frecuentes

### Operación Local
```bash
# Entrar a la carpeta de infraestructura
cd local

# Levantar todo el sistema (BD, LocalStack, API, Worker, Frontend)
docker compose up -d

# Visualizar logs del Worker para debuggear procesamiento
docker compose logs -f worker

# Forzar reaprovisionamiento de AWS (SQS/S3)
docker exec localstack_main /etc/localstack/init/ready.d/init-aws.sh
```

### Calidad y Testing
```bash
# Ejecutar suite completa con Pytest (requiere entorno arriba para E2E)
pytest

# Ejecutar solo tests unitarios (sin dependencia de LocalStack)
pytest -m "not localstack"
```

---

## 4. Patrones de Operación (Cómo funciona)

### Flujo de Mensajería (SQS)
1. La API recibe una solicitud en `POST /jobs`.
2. Llama a `aws.py -> send_job_request_to_sqs(job_id, type)`.
3. El mensaje entra a `reports-queue`.
4. El Worker (`worker/main.py`) usa **Long Polling** para extraer el mensaje, procesarlo y subir el resultado a S3.

### Notificaciones Push (WebSockets)
1. El Frontend abre una conexión en `/ws?token=...`.
2. El backend registra la conexión en el `ConnectionManager` (`services/notifier.py`).
3. Un bucle interno en `api/routers/websocket.py` consulta la base de datos por cambios de estado.
4. Al detectar un cambio (ej. `PENDING` -> `COMPLETED`), se envía un JSON al cliente con el nuevo estado y el `download_url` enriquecido.

---

## 5. Patrones de Extensión: Cómo añadir un nuevo tipo de reporte (ej. XLSX)

Si se requiere soportar un nuevo formato, siga estos pasos:

1.  **Backend (Modelos):** En `backend/app/models/job.py`, añadir `XLSX` al Enum de `report_type`.
2.  **Backend (Worker):** En `backend/app/worker/main.py`, añadir la lógica en el bloque de procesamiento para generar un archivo `.xlsx` (librerías como `pandas` u `openpyxl`).
3.  **Frontend:** En la vista de creación de reportes (Dashboard), añadir el botón o opción para seleccionar `XLSX`.
4.  **AWS:** El bucket de S3 aceptará el nuevo formato automáticamente gracias a las políticas genéricas configuradas.

---

## 6. Troubleshooting (Errores Comunes)

*   **Error 503 (Circuit Breaker Abierto):** Indica que la base de datos o LocalStack están caídos o saturados. Verifique con `docker ps` que todos los servicios estén `healthy`.
*   **Errores de Conectividad con AWS:** Si el backend lanza "Queue not found", ejecute el script de aprovisionamiento `init-aws.sh` manualmente.
*   **CORS en S3:** Si el navegador bloquea la descarga del reporte, asegúrese de que la sección de CORS en `init-aws.sh` se haya aplicado correctamente al bucket `prosperas-reports-bucket`.

---

> [!IMPORTANT]
> La integridad de la comunicación SQS-Worker es vital. Cualquier cambio en el esquema del mensaje en `send_job_request_to_sqs` debe replicarse inmediatamente en el `json.loads` del Worker.
