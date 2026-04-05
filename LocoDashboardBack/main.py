from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
import app.models  # noqa: F401 — registers models on Base.metadata
from app.routers.ingest import router as ingest_router
from app.routers.locomotives import router as locos_router
from app.routers.ws import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="LocoDashboardBack", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(ingest_router, prefix="/api")
app.include_router(locos_router, prefix="/api")
app.include_router(ws_router)


@app.get("/")
async def root():
    return {"service": "LocoDashboardBack", "status": "ok"}
