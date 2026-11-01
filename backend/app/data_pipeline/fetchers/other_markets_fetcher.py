from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
import yfinance as yf

FRANKFURTER_URL = "https://api.frankfurter.dev/v2"
TEJHQ_URL = "https://api.tejhq.dev/v1/ohlcv"

# Frankfurter provides daily reference exchange rates, not live/intraday prices.
FOREX_PAIRS = {
    "USD/INR": ("USD", "INR"),
    "EUR/USD": ("EUR", "USD"),
    "GBP/USD": ("GBP", "USD"),
    "USD/JPY": ("USD", "JPY"),
    "USD/CHF": ("USD", "CHF"),
    "AUD/USD": ("AUD", "USD"),
    "USD/CAD": ("USD", "CAD"),
    "NZD/USD": ("NZD", "USD"),
    "EUR/GBP": ("EUR", "GBP"),
    "EUR/JPY": ("EUR", "JPY"),
    "GBP/JPY": ("GBP", "JPY"),
    "USD/SGD": ("USD", "SGD"),
}

# Yahoo Finance symbols for Indian indices and NSE-listed equities.
# The existing TejHQ path is retained for RELIANCE, TCS and INFY.
# Additional stocks use Yahoo Finance daily historical data.
INDIA_SYMBOLS = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANK NIFTY": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "SBIN": "SBIN.NS",
    "BHARTIARTL": "BHARTIARTL.NS",
    "ITC": "ITC.NS",
    "LT": "LT.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
    "KOTAKBANK": "KOTAKBANK.NS",
    "AXISBANK": "AXISBANK.NS",
    "MARUTI": "MARUTI.NS",
    "M&M": "M&M.NS",
    "TATAMOTORS": "TATAMOTORS.NS",
    "TATASTEEL": "TATASTEEL.NS",
    "JSWSTEEL": "JSWSTEEL.NS",
    "SUNPHARMA": "SUNPHARMA.NS",
    "TITAN": "TITAN.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "BAJAJFINSV": "BAJAJFINSV.NS",
    "ASIANPAINT": "ASIANPAINT.NS",
    "WIPRO": "WIPRO.NS",
    "HCLTECH": "HCLTECH.NS",
    "ADANIENT": "ADANIENT.NS",
    "NTPC": "NTPC.NS",
    "POWERGRID": "POWERGRID.NS",
    "ONGC": "ONGC.NS",
    "COALINDIA": "COALINDIA.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS",
    "DMART": "DMART.NS",
    "TRENT": "TRENT.NS",
}


def _period_days(period: str) -> int:
    return {"1D": 1, "1W": 7, "1M": 30, "1Y": 365}.get(period.upper(), 30)


def _timestamp_ms_for_date(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1000)


async def get_forex_history(symbol: str, period: str = "1M") -> dict[str, Any]:
    symbol = symbol.upper()
    if symbol not in FOREX_PAIRS:
        raise ValueError(f"Unsupported forex pair: {symbol}")

    base, quote = FOREX_PAIRS[symbol]
    requested_days = _period_days(period)
    # Daily rates have no weekend/holiday observations; fetch a wider calendar window.
    effective_days = max(requested_days, 7)
    end_date = date.today()
    start_date = end_date - timedelta(days=effective_days + 5)

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            f"{FRANKFURTER_URL}/rates",
            params={
                "base": base,
                "quotes": quote,
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
            },
        )
        response.raise_for_status()
        rows = response.json()

    prices = []
    for row in rows:
        rate = row.get("rate")
        row_date = row.get("date")
        if isinstance(rate, (int, float)) and row_date:
            dt = date.fromisoformat(row_date)
            prices.append({
                "timestamp": _timestamp_ms_for_date(dt),
                "value": float(rate),
                "date": row_date,
            })

    prices.sort(key=lambda point: point["timestamp"])
    if not prices:
        raise RuntimeError(f"No daily reference rates returned for {symbol}")

    cutoff_date = end_date - timedelta(days=effective_days)
    filtered = [point for point in prices if date.fromisoformat(point["date"]) >= cutoff_date]

    return {
        "symbol": symbol,
        "market": "Forex",
        "source": "Frankfurter",
        "data_type": "daily_reference_rate",
        "requested_period": period.upper(),
        "intraday_available": False,
        "prices": filtered or prices,
    }


async def get_forex_prices() -> list[dict[str, Any]]:
    results = []
    for symbol in FOREX_PAIRS:
        try:
            history = await get_forex_history(symbol, "1W")
            points = history["prices"]
            latest = points[-1]
            previous = points[-2] if len(points) > 1 else None
            change = None
            if previous and previous["value"]:
                change = (latest["value"] - previous["value"]) / previous["value"] * 100

            results.append({
                "symbol": symbol,
                "name": symbol,
                "price": latest["value"],
                "as_of": latest["date"],
                "change_percent": change,
                "source": "Frankfurter",
                "data_type": "daily_reference_rate",
            })
        except (httpx.HTTPError, RuntimeError, ValueError):
            # One unavailable pair should not hide the other pairs.
            continue

    if not results:
        raise RuntimeError("No forex pairs could be fetched from Frankfurter")
    return results


def _yahoo_history(symbol: str, days: int) -> list[dict[str, Any]]:
    end = date.today() + timedelta(days=1)
    start = date.today() - timedelta(days=days + 10)

    frame = yf.Ticker(symbol).history(
        start=start.isoformat(),
        end=end.isoformat(),
        interval="1d",
        auto_adjust=False,
    )

    if frame.empty:
        raise RuntimeError(f"No daily history returned for {symbol}")

    prices = []
    for index, row in frame.iterrows():
        close = row.get("Close")
        if close is None:
            continue
        try:
            value = float(close)
        except (TypeError, ValueError):
            continue
        if value != value:  # NaN check
            continue

        prices.append({
            "timestamp": int(index.timestamp() * 1000),
            "value": value,
            "date": index.strftime("%Y-%m-%d"),
        })

    if not prices:
        raise RuntimeError(f"No usable closing prices returned for {symbol}")
    return prices[-max(2, days):]


async def get_india_history(symbol: str, period: str = "1M") -> dict[str, Any]:
    symbol = symbol.upper()
    if symbol not in INDIA_SYMBOLS:
        raise ValueError(f"Unsupported Indian instrument: {symbol}")

    days = _period_days(period)
    yahoo_symbol = INDIA_SYMBOLS[symbol]

    if symbol in {"RELIANCE", "TCS", "INFY"}:
        end_date = date.today()
        start_date = end_date - timedelta(days=days + 10)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{TEJHQ_URL}/nse/{symbol}",
                params={
                    "from": start_date.isoformat(),
                    "to": end_date.isoformat(),
                },
            )
            response.raise_for_status()
            payload = response.json()

        rows = payload.get("data", [])
        prices = []
        for row in rows:
            close = row.get("close")
            row_date = row.get("date")
            if isinstance(close, (int, float)) and row_date:
                dt = date.fromisoformat(row_date)
                prices.append({
                    "timestamp": _timestamp_ms_for_date(dt),
                    "value": float(close),
                    "date": row_date,
                })
        prices.sort(key=lambda point: point["timestamp"])
        prices = prices[-max(2, days):]
        source = "TejHQ / NSE end-of-day"
    else:
        prices = _yahoo_history(yahoo_symbol, days)
        source = "Yahoo Finance via yfinance (daily historical)"

    if not prices:
        raise RuntimeError(f"No historical prices returned for {symbol}")

    return {
        "symbol": symbol,
        "market": "India",
        "source": source,
        "data_type": "daily_close",
        "requested_period": period.upper(),
        "intraday_available": False,
        "prices": prices,
    }


async def get_india_prices() -> list[dict[str, Any]]:
    results = []
    for symbol in INDIA_SYMBOLS:
        try:
            history = await get_india_history(symbol, "1M")
            points = history["prices"]
            latest = points[-1]
            previous = points[-2] if len(points) > 1 else None
            change = None
            if previous and previous["value"]:
                change = (latest["value"] - previous["value"]) / previous["value"] * 100

            results.append({
                "symbol": symbol,
                "name": symbol,
                "price": latest["value"],
                "as_of": latest["date"],
                "change_percent": change,
                "source": history["source"],
                "data_type": "daily_close",
            })
        except (httpx.HTTPError, RuntimeError, ValueError, KeyError):
            # One symbol failing at the provider should not hide the rest.
            continue

    if not results:
        raise RuntimeError("No Indian market instruments could be fetched")
    return results
