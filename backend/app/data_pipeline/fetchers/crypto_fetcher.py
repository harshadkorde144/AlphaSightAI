import httpx

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

# CoinGecko IDs are used by both the prices and historical-price endpoints.
# Public API availability/rate limits are controlled by CoinGecko.
COINS = {
    "bitcoin": ("BTC", "Bitcoin"),
    "ethereum": ("ETH", "Ethereum"),
    "solana": ("SOL", "Solana"),
    "binancecoin": ("BNB", "BNB"),
    "ripple": ("XRP", "XRP"),
    "cardano": ("ADA", "Cardano"),
    "dogecoin": ("DOGE", "Dogecoin"),
    "tron": ("TRX", "TRON"),
    "the-open-network": ("TON", "Toncoin"),
    "avalanche-2": ("AVAX", "Avalanche"),
    "chainlink": ("LINK", "Chainlink"),
    "stellar": ("XLM", "Stellar"),
    "sui": ("SUI", "Sui"),
    "polkadot": ("DOT", "Polkadot"),
    "litecoin": ("LTC", "Litecoin"),
    "bitcoin-cash": ("BCH", "Bitcoin Cash"),
    "shiba-inu": ("SHIB", "Shiba Inu"),
    "uniswap": ("UNI", "Uniswap"),
    "near": ("NEAR", "NEAR Protocol"),
    "aptos": ("APT", "Aptos"),
}

SYMBOL_TO_ID = {symbol: coin_id for coin_id, (symbol, _name) in COINS.items()}


async def get_crypto_prices() -> list[dict]:
    params = {
        "ids": ",".join(COINS),
        "vs_currencies": "usd,inr",
        "include_24hr_change": "true",
        "include_24hr_vol": "true",
        "include_market_cap": "true",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(COINGECKO_URL, params=params)
            response.raise_for_status()
            payload = response.json()

        results = []
        # Skip an individual missing coin instead of failing the entire market list.
        for coin_id, (symbol, name) in COINS.items():
            item = payload.get(coin_id)
            if not isinstance(item, dict) or "usd" not in item or "inr" not in item:
                continue
            results.append({
                "symbol": symbol,
                "name": name,
                "price_usd": item["usd"],
                "price_inr": item["inr"],
                "change_24h_percent": item.get("usd_24h_change"),
                "volume_24h_usd": item.get("usd_24h_vol"),
                "market_cap_usd": item.get("usd_market_cap"),
            })
        if not results:
            raise RuntimeError("Crypto provider returned no usable coin prices")
        return results

    except httpx.TimeoutException as exc:
        raise RuntimeError("Crypto market API timed out") from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Crypto market API returned HTTP {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError("Unable to connect to crypto market API") from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("Invalid crypto market data received") from exc


HISTORY_URL = "https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"


async def get_crypto_history(symbol: str, days: int) -> dict:
    symbol = symbol.upper()

    if symbol not in SYMBOL_TO_ID:
        raise ValueError(f"Unsupported crypto symbol: {symbol}")

    if days not in (1, 7, 30, 365):
        raise ValueError("Days must be 1, 7, 30, or 365")

    params = {"vs_currency": "usd", "days": days}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                HISTORY_URL.format(coin_id=SYMBOL_TO_ID[symbol]),
                params=params,
            )
            response.raise_for_status()
            payload = response.json()

        prices = payload.get("prices", [])
        if not prices:
            raise RuntimeError("Historical price data is empty")

        return {
            "symbol": symbol,
            "days": days,
            "prices": [
                {"timestamp": int(point[0]), "price_usd": float(point[1])}
                for point in prices
                if isinstance(point, (list, tuple)) and len(point) >= 2
            ],
        }

    except httpx.TimeoutException as exc:
        raise RuntimeError("Historical market API timed out") from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Historical market API returned HTTP {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError("Unable to connect to historical market API") from exc
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise RuntimeError("Invalid historical market data received") from exc
