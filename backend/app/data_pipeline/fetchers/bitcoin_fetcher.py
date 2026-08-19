import httpx

from backend.app.schemas.market import BitcoinMarketData


COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"


async def get_bitcoin_price() -> BitcoinMarketData:
    params = {
        "ids": "bitcoin",
        "vs_currencies": "usd,inr",
        "include_24hr_change": "true",
        "include_24hr_vol": "true",
        "include_market_cap": "true",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(COINGECKO_URL, params=params)
            response.raise_for_status()

            data = response.json()

        bitcoin = data["bitcoin"]

        return BitcoinMarketData(
            symbol="BTC",
            price_usd=bitcoin["usd"],
            price_inr=bitcoin["inr"],
            change_24h_percent=bitcoin["usd_24h_change"],
            volume_24h_usd=bitcoin["usd_24h_vol"],
            market_cap_usd=bitcoin["usd_market_cap"],
        )

    except httpx.TimeoutException as exc:
        raise RuntimeError("Bitcoin market API request timed out") from exc

    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Bitcoin market API returned HTTP {exc.response.status_code}"
        ) from exc

    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("Invalid Bitcoin market data received") from exc

    except httpx.RequestError as exc:
        raise RuntimeError("Unable to connect to Bitcoin market API") from exc