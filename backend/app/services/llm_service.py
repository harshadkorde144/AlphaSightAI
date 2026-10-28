from groq import AsyncGroq

from backend.app.core.config import settings
from backend.app.schemas.market import BitcoinMarketData

GROQ_MODEL = "llama-3.1-8b-instant"

_client: AsyncGroq | None = None


async def answer_bitcoin_question(
    question: str,
    market_data: BitcoinMarketData,
) -> str:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)

    system_prompt = (
        "You answer Bitcoin market questions using the live market snapshot provided. "
        "Be concise and factual. Do not invent prices."
    )
    user_content = (
        f"Question: {question}\n\n"
        f"BTC price USD: {market_data.price_usd}\n"
        f"BTC price INR: {market_data.price_inr}\n"
        f"24h change %: {market_data.change_24h_percent}\n"
        f"24h volume USD: {market_data.volume_24h_usd}\n"
        f"Market cap USD: {market_data.market_cap_usd}"
    )

    try:
        response = await _client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=512,
        )
    except Exception as exc:
        raise RuntimeError("The LLM provider could not complete the request") from exc

    try:
        answer = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise RuntimeError("The LLM provider returned an invalid response") from exc

    if not answer or not answer.strip():
        raise RuntimeError("The LLM provider returned an empty answer")

    return answer.strip()
