import json

from groq import AsyncGroq

from backend.app.core.config import settings
from backend.app.schemas.market import BitcoinMarketData


_client = AsyncGroq(api_key=settings.groq_api_key)


async def answer_bitcoin_question(
    question: str,
    market_data: BitcoinMarketData,
) -> str:
    """Answer a Bitcoin question grounded in the latest fetched market snapshot."""
    market_snapshot = json.dumps(
        market_data.model_dump(),
        ensure_ascii=False,
        separators=(",", ":"),
    )

    try:
        response = await _client.chat.completions.create(
            model=settings.groq_model,
            temperature=0.2,
            max_tokens=700,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are AlphaSightAI's Bitcoin market research assistant. "
                        "Answer clearly and concisely. Use the supplied market snapshot "
                        "for current prices and metrics. Distinguish facts from analysis, "
                        "do not invent missing data, and never present market predictions "
                        "as guaranteed financial advice. If the snapshot does not answer "
                        "the question, say what information is missing."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question: {question}\n\n"
                        f"Latest market snapshot (JSON): {market_snapshot}"
                    ),
                },
            ],
        )
    except Exception as exc:
        raise RuntimeError("The LLM provider could not complete the request") from exc

    answer = response.choices[0].message.content
    if not answer or not answer.strip():
        raise RuntimeError("The LLM provider returned an empty answer")

    return answer.strip()
