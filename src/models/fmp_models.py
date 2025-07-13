from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator


class FMPArticle(BaseModel):
    """Single article object returned by /stable/fmp-articles."""

    title: str
    date: datetime
    content: str
    tickers: list[str] = Field(alias="tickers")
    image: HttpUrl | None = None
    link: HttpUrl
    author: str | None = None
    site: str | None = None

    # Convert comma‑separated string → list[str]
    @field_validator("tickers", mode="before")
    def split_tickers(cls, v):  # noqa: D401  (“/plain‑function docstring”) pylint: disable=no-self-argument
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v


class FMPArticlesResponse(BaseModel):
    """Wrapper aligning with NewsResponse shape (status + total results)."""

    status: str = "ok"
    total_results: int = Field(alias="totalResults")
    articles: list[FMPArticle]
