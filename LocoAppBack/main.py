import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine
import app.models  # noqa: F401 — registers models on Base.metadata
from app.generator import run_generator
from app.mqtt_publisher import run_mqtt_publisher
from app.register import register_in_dashboard
from app.routers.maintenance import router as maintenance_router
from app.routers.ws import router as ws_router

if os.getenv("DASHBOARD_URL"):
    DASHBOARD_URL = os.getenv("DASHBOARD_URL")
else:
    dashboard_host = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    dashboard_port = os.getenv("DASHBOARD_PORT", "9000")
    DASHBOARD_URL = f"http://{dashboard_host}:{dashboard_port}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await register_in_dashboard(DASHBOARD_URL)
    gen_task = asyncio.create_task(run_generator())
    pub_task = asyncio.create_task(run_mqtt_publisher())
    yield
    gen_task.cancel()
    pub_task.cancel()
    await engine.dispose()


app = FastAPI(title="LocoAppBack", lifespan=lifespan)
app.include_router(ws_router)
app.include_router(maintenance_router)


@app.get("/")
async def root():
    return {"service": "LocoAppBack", "status": "ok"}
