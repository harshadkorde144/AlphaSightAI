
import inspect
import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings

# Market fetchers
from backend.app.data_pipeline.fetchers.bitcoin_fetcher import (
    get_bitcoin_price,
)
from backend.app.data_pipeline.fetchers.crypto_fetcher import (
    get_crypto_prices,
    get_crypto_history,
)
from backend.app.data_pipeline.fetchers.other_markets_fetcher import (
    get_forex_prices,
    get_forex_history,
    get_india_prices,
    get_india_history,
)

# Bitcoin AI
from backend.app.schemas.bitcoin_qa import (
    BitcoinAnswer,
    BitcoinQuestion,
)
from backend.app.schemas.market import BitcoinMarketData
from backend.app.services.llm_service import answer_bitcoin_question

# RAG Research
from backend.app.schemas.research import (
    ResearchSearchRequest,
    ResearchSearchResponse,
)
from rag.vector_store import search_knowledge_base
from fastapi import HTTPException
from backend.app.services.news_service import FEEDS, get_news


# ==========================================
# LOGGING
# ==========================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AlphaSightAI")


# ==========================================
# HELPER: SYNC + ASYNC COMPATIBILITY
# ==========================================

async def resolve_result(function, *args, **kwargs):
    """
    Supports both synchronous and asynchronous functions.
    """
    result = function(*args, **kwargs)

    if inspect.isawaitable(result):
        result = await result

    return result


# ==========================================
# FASTAPI APPLICATION
# ==========================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AlphaSightAI - LLM-powered Multi-Agent RAG "
        "System for Financial Market Intelligence"
    ),
)


# ==========================================
# CORS CONFIGURATION
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# ROOT & HEALTH
# ==========================================

@app.get("/")
async def root():
    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "message": "Welcome to AlphaSightAI API",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "application": settings.app_name,
        "version": settings.app_version,
    }

# ============================================
# NEWS
# ============================================

@app.get("/api/v1/news/{category}")
def news(category: str):
    if category not in FEEDS:
        raise HTTPException(status_code=404, detail="Unknown category")
    return get_news(category)

# ==========================================
# BITCOIN MARKET
# ==========================================

@app.get(
    "/api/v1/market/bitcoin/price",
    response_model=BitcoinMarketData,
)
async def bitcoin_price():
    try:
        return await resolve_result(get_bitcoin_price)

    except Exception as exc:
        logger.exception("Bitcoin price fetch failed")
        raise HTTPException(
            status_code=503,
            detail=f"Unable to fetch Bitcoin price: {str(exc)}",
        )


# ==========================================
# CRYPTO MARKET
# ==========================================

@app.get("/api/v1/market/crypto/prices")
async def crypto_prices():
    try:
        return await resolve_result(get_crypto_prices)

    except Exception as exc:
        logger.exception("Crypto prices fetch failed")
        raise HTTPException(
            status_code=503,
            detail=f"Unable to fetch crypto prices: {str(exc)}",
        )


@app.get("/api/v1/market/crypto/history")
async def crypto_history(
    symbol: str = Query(..., min_length=1),
    days: int = Query(30),
):
    if days not in (1, 7, 30, 365):
        raise HTTPException(
            status_code=400,
            detail="Days must be 1, 7, 30 or 365",
        )

    try:
        return await resolve_result(
            get_crypto_history,
            symbol.upper().strip(),
            days,
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        logger.exception("Crypto history fetch failed")
        raise HTTPException(
            status_code=503,
            detail=f"Unable to fetch crypto history: {str(exc)}",
        )


# ==========================================
# FOREX MARKET
# ==========================================

@app.get("/api/v1/market/forex/prices")
async def forex_prices():
    try:
        return await resolve_result(get_forex_prices)

    except Exception as exc:
        logger.exception("Forex prices fetch failed")
        raise HTTPException(
            status_code=503,
            detail=f"Unable to fetch forex prices: {str(exc)}",
        )


@app.get("/api/v1/market/forex/history")
async def forex_history(
    symbol: str = Query(..., min_length=1),
    period: str = Query("1M"),
):
    try:
        return await resolve_result(
            get_forex_history,
            symbol.upper().strip(),
            period.upper().strip(),
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        logger.exception("Forex history fetch failed")
        raise HTTPException(
            status_code=503,
            detail=f"Unable to fetch forex history: {str(exc)}",
        )


# ==========================================
# INDIAN STOCK MARKET
# ==========================================

@app.get("/api/v1/market/india/prices")
async def india_prices():
    try:
        return await resolve_result(get_india_prices)

    except Exception as exc:
        logger.exception("Indian market prices fetch failed")
        raise HTTPException(
            status_code=503,
            detail=f"Unable to fetch Indian market prices: {str(exc)}",
        )


@app.get("/api/v1/market/india/history")
async def india_history(
    symbol: str = Query(..., min_length=1),
    period: str = Query("1M"),
):
    try:
        return await resolve_result(
            get_india_history,
            symbol.upper().strip(),
            period.upper().strip(),
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        logger.exception("Indian market history fetch failed")
        raise HTTPException(
            status_code=503,
            detail=f"Unable to fetch Indian market history: {str(exc)}",
        )


# ==========================================
# BITCOIN AI QUESTION & ANSWER
# ==========================================



@app.post(
    "/api/v1/bitcoin/ask",
    response_model=BitcoinAnswer,
)
async def ask_bitcoin_question(
    request: BitcoinQuestion,
):
    try:
        market_data = await resolve_result(get_bitcoin_price)

        answer = await resolve_result(
            answer_bitcoin_question,
            request.question,
            market_data,
        )

        return BitcoinAnswer(
            question=request.question,
            market_data=(
                market_data.model_dump()
                if hasattr(market_data, "model_dump")
                else market_data
            ),
            answer=answer,
        )

    except Exception as exc:
        logger.exception("Bitcoin AI response failed")

        raise HTTPException(
            status_code=500,
            detail=f"Bitcoin AI response failed: {str(exc)}",
        )



# ==========================================
# RAG RESEARCH SEARCH
# ==========================================


@app.post(
    "/api/v1/research/search",
    response_model=ResearchSearchResponse,
)
async def research_search(
    request: ResearchSearchRequest,
):
    try:
        results = await resolve_result(
            search_knowledge_base,
            request.query,
            request.top_k,
        )

        return ResearchSearchResponse(
            query=request.query,
            results=results,
            result_count=len(results),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        logger.exception("Research search failed")

        raise HTTPException(
            status_code=500,
            detail=f"Research search failed: {str(exc)}",
        )


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
