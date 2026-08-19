import httpx


COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"


async def get_bitcoin_price() -> dict:
    params = {
        "ids": "bitcoin",
        "vs_currencies": "usd,inr",
        "include_24hr_change": "true",
        "include_24hr_vol": "true",
        "include_market_cap": "true",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(COINGECKO_URL, params=params)
        response.raise_for_status()

        data = response.json()

    bitcoin = data["bitcoin"]

    return {
        "symbol": "BTC",
        "price_usd": bitcoin.get("usd"),
        "price_inr": bitcoin.get("inr"),
        "change_24h_percent": bitcoin.get("usd_24h_change"),
        "volume_24h_usd": bitcoin.get("usd_24h_vol"),
        "market_cap_usd": bitcoin.get("usd_market_cap"),
    }