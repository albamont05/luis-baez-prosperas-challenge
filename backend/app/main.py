from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.db import init_db
from app.api.routers import jobs, auth
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

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(CircuitBreakerOpenException, circuit_breaker_exception_handler)

app.include_router(auth.router)
app.include_router(jobs.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
