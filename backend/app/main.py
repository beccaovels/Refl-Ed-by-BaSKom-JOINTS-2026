from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audio, auth, materials, profiles, reports, schedule, sessions, signals
from app.core.config import APP_NAME, settings
from app.core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# Routers from app/api/ are included here as they are written (see docs/api-contract.md).
app.include_router(auth.router, prefix="/api")
app.include_router(profiles.router, prefix="/api")
app.include_router(materials.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(audio.router, prefix="/api")
app.include_router(signals.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(schedule.router, prefix="/api")
