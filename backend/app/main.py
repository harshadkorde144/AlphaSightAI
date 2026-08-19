from fastapi import FastAPI
from backend.app.schemas.market import BitcoinMarketData
from backend.app.core.config import settings
from backend.app.data_pipeline.fetchers.bitcoin_fetcher import get_bitcoin_price

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
@app.get("/api/v1/market/bitcoin/price")
async def bitcoin_price():
    return await get_bitcoin_price()

@app.get(
    "/api/v1/market/bitcoin/price",
    response_model=BitcoinMarketData,
)
async def bitcoin_price():
    return await get_bitcoin_price()