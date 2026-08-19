from pydantic import BaseModel


class BitcoinMarketData(BaseModel):
    symbol: str
    price_usd: float
    price_inr: float
    change_24h_percent: float
    volume_24h_usd: float
    market_cap_usd: float