from datetime import datetime
from enum import Enum

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

    # Convert comma-separated string -> list[str]
    @field_validator("tickers", mode="before")
    def split_tickers(cls, v):  # noqa: D401  ("/plain-function docstring") pylint: disable=no-self-argument
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v


class FMPArticlesResponse(BaseModel):
    """Wrapper aligning with NewsResponse shape (status + total results)."""

    status: str = "ok"
    total_results: int = Field(alias="totalResults")
    articles: list[FMPArticle]


class FreeRiskAPI(str, Enum):
    ECONOMICS_CALENDAR = "/api/v3/economic_calendar?from={from}&to={to}"
    STANDARD_DEVIATION = "/api/v3/technical_indicator/{timeframe}/{symbol}?type=standardDeviation&period={period}"
    KEY_METRICS_TTM = "/api/v3/key-metrics-ttm/{symbol}"
    BALANCE_SHEET_GROWTH = (
        "/api/v3/balance-sheet-statement-growth/{symbol}?period=annual"
    )
    COMPANY_PROFILE = "/api/v3/profile/{symbol}"
    FINANCIAL_RATIOS = "/api/v3/ratios/symbol={symbol}"
    DELISTED_COMPANIES = "/api/v3/delisted-companies?page={page}"
    EARNINGS_CALENDAR = "/api/v3/earning_calendar?from={from}&to={to}"
    FMP_ARTICLES = "/api/v3/fmp/articles?page={page}&size={size}"
