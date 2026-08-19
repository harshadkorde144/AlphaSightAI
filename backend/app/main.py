from fastapi import FastAPI

from backend.app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    description="LLM-powered Multi-Agent RAG System for Real-Time Financial Market Intelligence",
    version=settings.app_version,
)


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "status": "running",
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }