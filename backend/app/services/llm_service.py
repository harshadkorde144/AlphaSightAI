
import json
import logging

from groq import AsyncGroq
from starlette.concurrency import run_in_threadpool

from backend.app.core.config import settings
from rag.vector_store import search_knowledge_base

logger = logging.getLogger(__name__)

_client = AsyncGroq(api_key=settings.groq_api_key)


async def answer_bitcoin_question(
    question: str,
    market_data,
) -> str:
    """Answer Bitcoin questions using market data and RAG context."""

    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    market_snapshot = json.dumps(
        market_data.model_dump()
        if hasattr(market_data, "model_dump")
        else market_data,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )

    research_context = (
        "No relevant research documents were retrieved."
    )

    # RAG retrieval is optional.
    try:
        research_results = await run_in_threadpool(
            search_knowledge_base,
            question,
            top_k=3,
        )

        if research_results:
            research_context = "\n\n".join(
                (
                    f"Source: {item.get('source', 'Unknown')}\n"
                    f"Research excerpt: {item.get('text', '')}"
                )
                for item in research_results
            )

    except Exception:
        logger.exception(
            "RAG retrieval failed. Continuing without research context."
        )

    # Groq LLM request.
    try:
        response = await _client.chat.completions.create(
            model=settings.groq_model,
            temperature=0.2,
            max_tokens=700,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AlphaSightAI's Bitcoin market research "
                        "assistant. Answer clearly and professionally. "
                        "Use the supplied market snapshot for current "
                        "market metrics. Use retrieved research only "
                        "as background information. Distinguish current "
                        "data from historical information. Never invent "
                        "missing values or guarantee financial returns. "
                        "Do not provide personalized financial advice."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question}\n\n"
                        f"Latest market snapshot:\n{market_snapshot}\n\n"
                        f"Retrieved research:\n{research_context}"
                    ),
                },
            ],
        )

    except Exception as exc:
        logger.exception("Groq API request failed")
        raise RuntimeError(
            "Groq could not complete the AI request. "
            "Check API key, model name and provider availability."
        ) from exc

    try:
        answer = response.choices[0].message.content

    except (AttributeError, IndexError, TypeError) as exc:
        logger.exception("Invalid Groq response")
        raise RuntimeError(
            "Groq returned an invalid response."
        ) from exc

    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("Groq returned an empty answer.")

    return answer.strip()
