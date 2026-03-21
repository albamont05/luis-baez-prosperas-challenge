from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # <-- Nuevo import
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.db import init_db
from app.api.routers import jobs, auth
from app.api.routers import websocket as ws_router
from app.services.aws import verify_aws_connectivity

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialización: Crear tablas de BD si no existen
    print("Inicializando base de datos...")
    await init_db()
    print("Base de datos lista.")
    
    print("Verificando conectividad con Infraestructura Cloud/AWS (Fail-Fast)...")
    await verify_aws_connectivity()
    print("AWS / LocalStack verificado exitosamente.")
    
    yield
    print("Shutting down...")

from app.core.circuit_breaker import CircuitBreakerOpenException
from app.api.errors import global_exception_handler, circuit_breaker_exception_handler

app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    lifespan=lifespan
)

# --- Configuración de CORS ---
origins = [
    "http://localhost",      # Frontend en Docker (puerto 80)
    "http://localhost:5173",    # Frontend Vite/React
    "http://127.0.0.1",  # Alternativa de IP
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# -----------------------------

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(CircuitBreakerOpenException, circuit_breaker_exception_handler)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(ws_router.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}