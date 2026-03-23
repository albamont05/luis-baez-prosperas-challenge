import asyncio
import logging
from typing import Optional

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.future import select

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.models.job import Job, JobStatus
from app.models.user import User
from app.schemas.job import JobResponse
from app.services.notifier import manager
from app.utils.s3 import enrich_job_with_download_url

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Estados terminales que merecen notificación activa
TERMINAL_STATUSES = {JobStatus.COMPLETED, JobStatus.FAILED}

# Intervalo de polling a la BD (segundos)
POLL_INTERVAL = 3


async def _authenticate_ws(token: Optional[str]) -> Optional[User]:
    """
    Valida el JWT recibido por query param y devuelve el User,
    o None si el token es inválido / ausente.
    """
    if not token:
        logger.warning("WebSocket: conexión sin token rechazada.")
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if not username:
            return None
    except jwt.InvalidTokenError as exc:
        logger.warning("WebSocket: token inválido — %s", exc)
        return None

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

    return user


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None, description="Bearer JWT token"),
):
    """
    Endpoint WebSocket para notificaciones en tiempo real de jobs.

    Conexión:  ws://<host>/ws?token=<jwt>

    Flujo:
      1. Valida el JWT desde query params.
      2. Registra la conexión en el ConnectionManager.
      3. Polling cada POLL_INTERVAL segundos consultando la BD.
      4. Envía JSON con el estado de cada job que cambia.
      5. Al desconectarse (cliente cierra pestaña), limpia el estado.
    """
    # ── Autenticación ──────────────────────────────────────────────
    user = await _authenticate_ws(token)
    if user is None:
        await websocket.close(code=4001)   # 4001 → Unauthorized
        logger.info("WebSocket: conexión cerrada por autenticación fallida.")
        return

    user_id = str(user.id)

    # ── Registro de conexión ───────────────────────────────────────
    await manager.connect(user_id, websocket)

    # Snapshot de estados ya conocidos para detectar cambios
    known_states: dict[str, str] = {} # job_id -> "status|result_url"

    try:
        while True:
            # ── Consulta a la BD ───────────────────────────────────
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Job).where(Job.user_id == user.id))
                jobs = result.scalars().all()

            for job in jobs:
                job_id_str = str(job.job_id)
                # Creamos una "firma" del estado actual
                current_state_signature = f"{job.status}|{job.result_url}"

            # Notificar si el estado O la URL cambiaron
            if known_states.get(job_id_str) != current_state_signature:
                known_states[job_id_str] = current_state_signature

                # Solo enviamos el mensaje si el status es terminal o hubo un cambio real
                job_resp = JobResponse.model_validate(job)
                enriched_job = await enrich_job_with_download_url(job_resp)

                payload = {
                    "event": "job_update",
                    "job_id": job_id_str,
                    "report_type": job.report_type,
                    "status": job.status,
                    "result_url": job.result_url,
                    "download_url": enriched_job.download_url,
                }
                
                # Verificación de seguridad: No enviar si es COMPLETED pero aún no hay URL
                if job.status == JobStatus.COMPLETED and not enriched_job.download_url:
                    # Retrocedemos el snapshot para intentar en la siguiente vuelta (dentro de 3s)
                    known_states[job_id_str] = f"{job.status}|NONE"
                    continue

                await manager.send_personal_message(user_id, payload)
                logger.info(
                        "Notificación enviada: user_id=%s job_id=%s status=%s",
                        user_id, job_id_str, current_status,
                    )

            await asyncio.sleep(POLL_INTERVAL)

    except WebSocketDisconnect:
        # Cliente cerró la pestaña / conexión de red perdida
        logger.info("WebSocket desconectado (cliente): user_id=%s", user_id)

    except Exception as exc:
        # Cualquier error inesperado → loguear y limpiar
        logger.error("WebSocket error para user_id=%s: %s", user_id, exc, exc_info=True)

    finally:
        # ── Limpieza: evitar fugas de memoria ─────────────────────
        manager.disconnect(user_id)
