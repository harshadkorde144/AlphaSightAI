
from pydantic import BaseModel, Field, ConfigDict


class ResearchSearchRequest(BaseModel):

    model_config = ConfigDict(
        str_strip_whitespace=True
    )

    query: str = Field(
        min_length=3,
        max_length=1000,
    )

    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
    )


class ResearchResult(BaseModel):

    source: str

    text: str

    chunk_number: int

    distance: float


class ResearchSearchResponse(BaseModel):

    query: str

    results: list[ResearchResult]

    result_count: int = Field(
        ge=0
    )
