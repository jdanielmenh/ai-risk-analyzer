"""General-purpose asynchronous wrapper for **Financial Modeling Prep (FMP)**
that ONLY uses endpoints disponibles en el **plan gratuito** (`stable/…`).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any, Literal

from src.errors.errors import APIError
from src.models.fmp_models import FMPArticle, FMPArticlesResponse
from src.utils.config import ClientsSettings

from .base_client import BaseAPIClient

settings = ClientsSettings()


class FMPAPIError(APIError):
    """Raised when FMP returns an error structure or HTTP failure."""


class FMPClient(BaseAPIClient):
    """Async wrapper around **free-tier** endpoints of Financial Modeling Prep."""

    BASE_URL = "https://financialmodelingprep.com"

    def __init__(self, api_key: str | None = None, *, timeout: int = 10) -> None:
        super().__init__(api_key or settings.fmp_api_key, timeout=timeout)

    async def _fmp_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        q = params.copy() if params else {}
        q["apikey"] = self._api_key
        data = await self._get(path, q)
        if isinstance(data, dict) and any(k.lower().startswith("error") for k in data):
            raise FMPAPIError(next(iter(data.values())))
        return data

    # --------------------------- Core financial data ---------------------------
    async def quote(self, symbols: Sequence[str] | str) -> list[dict[str, Any]]:
        syms = symbols if isinstance(symbols, str) else ",".join(symbols)
        return await self._fmp_get(f"/api/v3/quote/{syms}")

    async def profile(self, symbol: str) -> dict[str, Any]:
        data = await self._fmp_get(f"/api/v3/profile/{symbol}")
        return data[0] if isinstance(data, list) and data else {}

    async def historical_prices(
        self,
        symbol: str,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        serietype: Literal["line", "candles"] = "line",
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"serietype": serietype}
        if from_date:
            params["from"] = from_date.isoformat()
        if to_date:
            params["to"] = to_date.isoformat()
        return await self._fmp_get(
            f"/api/v3/historical-price-eod/full?{symbol}", params
        )

    # ---------------------------------- Articles ----------------------------------
    async def articles(
        self,
        *,
        page: int = 0,
        limit: int = 20,
    ) -> FMPArticlesResponse:
        """Latest FMP in-house articles (free tier)"""
        raw: list[dict[str, Any]] = await self._fmp_get(
            "/stable/fmp-articles",
            {"page": page, "limit": min(limit, 250)},
        )

        articles = [FMPArticle.model_validate(item) for item in raw]
        return FMPArticlesResponse.model_validate(
            {"totalResults": len(articles), "articles": articles}
        )
