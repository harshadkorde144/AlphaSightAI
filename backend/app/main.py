from fastapi import FastAPI, HTTPException

from backend.app.core.config import settings
from backend.app.data_pipeline.fetchers.bitcoin_fetcher import get_bitcoin_price
from backend.app.schemas.bitcoin_qa import BitcoinAnswer, BitcoinQuestion
from backend.app.schemas.market import BitcoinMarketData
from backend.app.services.llm_service import answer_bitcoin_question

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


@app.get(
    "/api/v1/market/bitcoin/price",
    response_model=BitcoinMarketData,
)
async def bitcoin_price():
    try:
        return await get_bitcoin_price()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@app.post(
    "/api/v1/bitcoin/ask",
    response_model=BitcoinAnswer,
)
async def ask_bitcoin(body: BitcoinQuestion):
    try:
        market_data = await get_bitcoin_price()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    try:
        answer = await answer_bitcoin_question(body.question, market_data)
    except RuntimeError:
        raise HTTPException(
            status_code=502,
            detail="Unable to generate a Bitcoin answer at this time",
        )

    return BitcoinAnswer(
        question=body.question,
        answer=answer,
        market_data=market_data,
    )
