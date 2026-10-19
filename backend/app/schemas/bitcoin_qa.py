from pydantic import BaseModel, Field


class BitcoinQuestion(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=1000,
        description="A question about Bitcoin or its current market data.",
    )


class BitcoinAnswer(BaseModel):
    question: str
    answer: str
    market_data: dict[str, str | float]
