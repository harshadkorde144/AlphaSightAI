from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.market import BitcoinMarketData


class BitcoinQuestion(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(
        min_length=3,
        max_length=1000,
    )


class BitcoinAnswer(BaseModel):
    question: str
    answer: str
    market_data: BitcoinMarketData
