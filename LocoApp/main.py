import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import REPORTER_API_KEY
from app.database import engine
import app.models  # noqa: F401 — registers models on Base.metadata
from app.reporter import run_reporter
from app.routers.ws import router as ws_router

DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:9000")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(run_reporter(DASHBOARD_URL, REPORTER_API_KEY))
    yield
    task.cancel()
    await engine.dispose()


app = FastAPI(title="LocoApp", lifespan=lifespan)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {"service": "LocoApp", "status": "ok"}
