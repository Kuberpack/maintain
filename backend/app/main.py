from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.routers import (
    auth,
    config,
    machines,
    part_replacements,
    photos,
    repair_logs,
    task_instances,
    task_types,
    users,
)
from app.scheduler import start_scheduler, stop_scheduler

settings = get_settings()

Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Machine Maintenance & Cleaning Tracker API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(config.router)
app.include_router(machines.router)
app.include_router(task_types.router)
app.include_router(users.router)
app.include_router(task_instances.router)
app.include_router(repair_logs.router)
app.include_router(part_replacements.router)
app.include_router(photos.router)

# Uploaded proof-of-completion photos. Unauthenticated (like the rest of the
# static filesystem would be) -- acceptable per architecture.md's "no public
# internet exposure, internal tool only", and filenames are unguessable UUIDs.
app.mount("/uploads", StaticFiles(directory=settings.uploads_dir), name="uploads")


@app.get("/health")
def health() -> dict:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
