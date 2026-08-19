from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.routers import (
    auth,
    config,
    machines,
    part_replacements,
    repair_logs,
    task_instances,
    task_types,
    users,
)

settings = get_settings()

app = FastAPI(title="Machine Maintenance & Cleaning Tracker API")

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


@app.get("/health")
def health() -> dict:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
