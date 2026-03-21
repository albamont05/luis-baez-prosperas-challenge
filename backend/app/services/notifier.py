import logging
from typing import Dict
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Gestiona las conexiones WebSocket activas, mapeando cada user_id
    a su WebSocket correspondiente. Sin Redis — estado en memoria del proceso.
    """

    def __init__(self):
        # { user_id (str) -> WebSocket }
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        """Acepta la conexión y registra el WebSocket para el user_id."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info("WebSocket conectado para user_id=%s | conexiones activas=%d",
                    user_id, len(self.active_connections))

    def disconnect(self, user_id: str) -> None:
        """Elimina la entrada del usuario al cerrar la conexión."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info("WebSocket desconectado para user_id=%s | conexiones activas=%d",
                        user_id, len(self.active_connections))

    async def send_personal_message(self, user_id: str, message: dict) -> None:
        """Envía un JSON al WebSocket del usuario indicado, si sigue conectado."""
        websocket = self.active_connections.get(user_id)
        if websocket:
            await websocket.send_json(message)
            logger.info("Mensaje enviado a user_id=%s: %s", user_id, message)
        else:
            logger.warning("send_personal_message: user_id=%s no tiene conexión activa.", user_id)


# Instancia singleton compartida por toda la aplicación
manager = ConnectionManager()
