"""
FastAPI entrypoint.

Run with:
    uvicorn backend.main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health")
def health():
    return {"status": "ok"}
