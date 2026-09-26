"""
FastAPI entrypoint.

Run with:
    uvicorn backend.main:app --reload --port 8000
"""
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pipeline import load  # noqa: E402

from .routers import analytics

app = FastAPI(
    title="DataFlow API",
    description="Weather & climate analytics for Lille (and comparison cities), backed by Open-Meteo.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(analytics.router)


@app.on_event("startup")
def ensure_schema_exists():
    """
    Create the schema if it doesn't exist yet. Makes the API resilient to
    being started before the pipeline has run once (e.g. `docker compose
    up -d` before `docker compose run pipeline ...`) -- endpoints will
    still return empty results rather than a database error until real
    data is loaded.
    """
    conn = load.get_connection()
    try:
        load.init_schema(conn)
    finally:
        conn.close()


@app.get("/health")
def health():
    return {"status": "ok"}
