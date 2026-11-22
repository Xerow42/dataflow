"""
FastAPI entrypoint.

Run with:
    uvicorn backend.main:app --reload --port 8000
"""
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pipeline import load  # noqa: E402

from .routers import analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create the schema before serving requests; release the connection."""
    conn = load.get_connection()
    try:
        load.init_schema(conn)
    finally:
        conn.close()
    yield


app = FastAPI(
    title="DataFlow API",
    description="Weather & climate analytics for Lille (and comparison cities), backed by Open-Meteo.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(analytics.router)


@app.get("/health")
def health():
    return {"status": "ok"}
