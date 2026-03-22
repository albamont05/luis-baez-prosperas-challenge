Este documento detalla la metodología de "Vibe Coding" y supervisión técnica empleada para cumplir con el Sistema de Procesamiento Asíncrono de Reportes de Prosperas. La implementación es un proceso iterativo de arquitectura, corrección y validación entre el desarrollador y Gemini 3.1 Pro.

1. Fase de Ingeniería de Prompts para el Scaffold InicialPara el desarrollo del Core, se diseñaron instrucciones estructuradas para evitar alucinaciones con librerías obsoletas:

Hito 1 - Prompt de Backend (FastAPI):

Prompt: "Genera un backend con FastAPI usando Pydantic v2 y SQLAlchemy asíncrono. Estructura el proyecto con una separación clara entre /api, /core y /services. El endpoint POST /jobs debe ser no bloqueante y publicar en Amazon SQS usando Aioboto3".

Resultado: Estructura de carpetas profesional con inyección de dependencias para la base de datos y un cliente SQS funcional.

Hito 2 - Prompt de Frontend (React):

Prompt: "Crea un Dashboard en React 19 con Vite y Tailwind CSS. Implementa un cliente de WebSockets para recibir actualizaciones de estado en tiempo real. No uses polling; el sistema debe reaccionar proactivamente a los cambios".

Resultado: Interfaz responsive con manejo de estados globales y conexión persistente a la API.

Hito 3 - Definición de Modelos y Esquemas:

Prompt: "Define un modelo de SQLModel para 'Job' que incluya job_id (UUID), status (Enum: PENDING, PROCESSING, COMPLETED, FAILED) y result_url. Asegura que los campos created_at y updated_at se manejen automáticamente".

Resultado: Esquema de base de datos robusto con validación de tipos nativa en Python.

Hito 4 - Dockerización Multietapa:

Prompt: "Crea un Dockerfile optimizado para FastAPI que use una imagen 'slim' y separe la instalación de dependencias de la copia del código para aprovechar la caché de capas".

Resultado: Imágenes de contenedor ligeras listas para ser desplegadas en AWS ECR.

Pivotaje de Infraestructura (Resolución de Problemas) Ante la restricción de cuotas de AWS para cuentas nuevas, se tomaron decisiones de liderazgo técnico:

Hito 5 - Identificación del Bloqueo: Se detectó el error de límite de servicios al intentar usar App Runner en la cuenta recién creada.

Hito 6 - Intervención Humana (Descarte de sugerencia IA): La IA sugirió esperar 24h por soporte técnico. Decidí ignorar la sugerencia y pivotar a EC2 + Docker Compose para cumplir con el plazo de 7 días.

Hito 7 - Configuración de Redes (Networking):

Prompt: "Dame la configuración de un archivo docker-compose.yml que levante la API y el Worker en la misma red bridge, exponiendo el puerto 8000 y asegurando que el Worker pueda resolver el nombre de host de la API".

Resultado: Orquestación local y de producción idénticas, garantizando el despliegue funcional.

Hito 8 - Resultado de Resiliencia: Se logró el despliegue en una URL pública real utilizando una instancia EC2, cumpliendo con el requisito obligatorio de visibilidad.3. Implementación de Resiliencia Avanzada (Retos Bonus B2, B3, B4) Uso de sesiones de Deep-Dive para implementar patrones Senior:

Hito 9 - Circuit Breaker (B2):

Prompt: "Implementa un patrón Circuit Breaker en Python para las llamadas a S3. Si falla 3 veces seguidas, debe abrir el circuito por 15 segundos y lanzar una excepción controlada".

Resultado: Sistema protegido contra fallos en cascada de servicios externos.

Hito 10 - WebSockets en Tiempo Real (B3):

Prompt: "Crea un ConnectionManager en FastAPI que use un diccionario en memoria para mapear active_connections. El Worker debe enviar un broadcast al socket cuando un Job cambie de estado en RDS".

Resultado: Experiencia de usuario fluida sin recargas de página.

Hito 11 - Back-off Exponencial (B4):

Prompt: "Añade una lógica de reintento con back-off exponencial al consumidor de SQS. El tiempo de espera debe aumentar tras cada fallo de conexión con el servicio".

Resultado: Reducción de carga en la infraestructura durante periodos de inestabilidad.

Hito 12 - Seguridad S3 (Pre-signed URLs):

Prompt: "Escribe una función en Aioboto3 y Boto3 que genere una URL firmada para un objeto privado en S3 con una expiración de exactamente 600 segundos".

Resultado: Acceso seguro y temporal a los reportes generados.4. Estrategia de Calidad: Testing Unitario y E2E.

Hito 13 - Unit Tests con Mocks (B6):

Prompt: "Genera tests con Pytest que usen unittest.mock para simular el cliente SQS. El test debe verificar que el mensaje enviado contenga el job_id correcto".

Resultado: Cobertura de código superior al 70% en lógica de negocio.

Hito 14 - Tests End-to-End (E2E):

Prompt: "Crea un script de integración que haga un POST a /jobs y luego verifique mediante WebSockets que el estado cambie a COMPLETED".

Resultado: Validación del flujo completo del sistema distribuido.

Hito 15 - Simulación de Fallos:

Prompt: "Simula un error de escritura en la base de datos durante el procesamiento del Worker y verifica que el mensaje regrese a la cola de SQS para reintento".

Resultado: Confirmación de la resiliencia y el desacoplamiento.

Hito 16 - Pipeline CI/CD (GitHub Actions):

Prompt: "Configura un flujo de GitHub Actions que haga build de la imagen, la suba a ECR y ejecute un comando SSH en mi EC2 para hacer docker-compose pull y up".

Resultado: Despliegue automatizado con historial de ejecuciones verde.

5. Documentación y Transferencia de Contexto

Hito 17 - El Prompt Maestro (SKILL.md):

Prompt: "Escanea el repositorio y genera un archivo de alta fidelidad que sirva como SSoT. Incluye el mapa de carpetas y los patrones para agregar nuevos reportes".

Resultado: Documento que permite a cualquier IA operar sobre el código con precisión.

Hito 18 - Ajuste de Calidad de Documentación:

Acción: Corregí manualmente el output de la IA para asegurar que el diagrama de arquitectura reflejara fielmente la conexión entre el Worker y SQS.

Hito 19 - Consolidación de TECHNICAL_DOCS.md:

Prompt: "Genera una tabla comparativa en Markdown que justifique por qué usamos SQS frente a RabbitMQ y RDS frente a DynamoDB para este reto".

Resultado: Documentación técnica clara que facilita la defensa del proyecto ante el evaluador.