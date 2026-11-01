
from pydantic import BaseModel, Field, ConfigDict


class BitcoinQuestion(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(
        min_length=3,
        max_length=2000,
        description="Question about Bitcoin and cryptocurrency markets",
    )


class BitcoinAnswer(BaseModel):
    question: str

    market_data: dict = Field(
        default_factory=dict
    )

    answer: str
