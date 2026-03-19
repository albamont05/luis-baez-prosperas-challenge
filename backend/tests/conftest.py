import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, AsyncMock

# 1. Patch de AWS verification que se corre en el lifespan ANTES de importar app
patcher_aws = patch("app.services.aws.verify_aws_connectivity", new_callable=AsyncMock)
patcher_aws.start()

# Importaciones de la app tras preparar parches críticos
from app.main import app
from app.core import db
from app.models.user import User
from app.models.job import Job
from app.core.db import Base 

# 2. Configurar SQLite en Memoria asegurando un StaticPool para compartir entre threads y dependencias
# Usamos un URI de caché compartida para asegurar que todas las conexiones de aiosqlite vean las tablas
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///file:testdb?mode=memory&cache=shared&uri=true"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

# 3. Forzar que toda la app use nuestra DB de pruebas para evitar fallos de aislamiento
db.engine = engine
db.AsyncSessionLocal = TestingSessionLocal

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[db.get_db] = override_get_db

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Crea y destruye la DB para aislando los tests en memoria"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
