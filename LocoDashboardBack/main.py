import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.database import engine, AsyncSessionLocal
import app.models  # noqa: F401 — registers models on Base.metadata
from app.models import User
from app.mqtt_subscriber import run_mqtt_subscriber
from app.routers.auth import router as auth_router, _hash_password
from app.routers.ingest import router as ingest_router
from app.routers.locomotives import router as locos_router
from app.routers.ws import router as ws_router

_DEFAULT_ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
_DEFAULT_ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "admin123")
_DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000,http://[::1]:3000"
_CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",") if o.strip()]


async def _seed_admin() -> None:
    """Create default admin user if no users exist."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none() is not None:
            return
        session.add(User(
            username=_DEFAULT_ADMIN_USER,
            hashed_password=_hash_password(_DEFAULT_ADMIN_PASS),
        ))
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _seed_admin()
    sub_task = asyncio.create_task(run_mqtt_subscriber())
    yield
    sub_task.cancel()
    await engine.dispose()


app = FastAPI(title="LocoDashboardBack", lifespan=lifespan)

from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(ingest_router, prefix="/api")
app.include_router(locos_router, prefix="/api")
app.include_router(ws_router)


@app.get("/")
async def root():
    return {"service": "LocoDashboardBack", "status": "ok"}
