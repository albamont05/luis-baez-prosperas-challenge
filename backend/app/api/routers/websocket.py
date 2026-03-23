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

# Intervalo de polling a la BD (segundos)
POLL_INTERVAL = 3

async def _authenticate_ws(token: Optional[str]) -> Optional[User]:
    """Valida el JWT recibido por query param."""
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
    user = await _authenticate_ws(token)
    if user is None:
        await websocket.close(code=4001)
        return

    user_id = str(user.id)
    await manager.connect(user_id, websocket)

    # Snapshot de estados: job_id -> "status|result_url"
    known_states: dict[str, str] = {}

    try:
        while True:
            # --- MEJORA DE SEGURIDAD ---
            # El sleep al INICIO garantiza que incluso si algo falla o hay un 'continue',
            # el CPU descanse al menos 3 segundos por cada iteración del bucle while.
            await asyncio.sleep(POLL_INTERVAL)

            async with AsyncSessionLocal() as db:
                # Consultamos los jobs del usuario
                result = await db.execute(
                    select(Job).where(Job.user_id == user.id)
                )
                jobs = result.scalars().all()

                for job in jobs:
                    job_id_str = str(job.job_id)
                    current_signature = f"{job.status}|{job.result_url}"

                    # Solo procesamos si algo cambió respecto a lo que ya notificamos
                    if known_states.get(job_id_str) != current_signature:
                        
                        job_resp = JobResponse.model_validate(job)
                        enriched_job = await enrich_job_with_download_url(job_resp)

                        # Verificación: Si está COMPLETED pero S3 aún no devuelve la URL enriquecida,
                        # NO actualizamos el snapshot y esperamos a la siguiente vuelta del while.
                        if job.status == JobStatus.COMPLETED and not enriched_job.download_url:
                            logger.info(f"Job {job_id_str} COMPLETED pero sin URL. Reintentando en {POLL_INTERVAL}s...")
                            continue 

                        # Si llegamos aquí, notificamos y actualizamos el snapshot
                        known_states[job_id_str] = current_signature

                        payload = {
                            "event": "job_update",
                            "job_id": job_id_str,
                            "report_type": job.report_type,
                            "status": job.status,
                            "result_url": job.result_url,
                            "download_url": enriched_job.download_url,
                        }

                        await manager.send_personal_message(user_id, payload)
                        logger.info(
                            "Notificación enviada: user_id=%s job_id=%s status=%s",
                            user_id, job_id_str, job.status
                        )

    except WebSocketDisconnect:
        logger.info("WebSocket desconectado (cliente): user_id=%s", user_id)
    except Exception as exc:
        logger.error("WebSocket error crítico para user_id=%s: %s", user_id, exc, exc_info=True)
    finally:
        manager.disconnect(user_id)