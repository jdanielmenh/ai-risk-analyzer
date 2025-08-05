import asyncio
from typing import Any, Literal

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from clients.fmp_client import FMPClient
from models.fmp_models import FreeRiskAPI

EndpointAlias = Literal[tuple(alias.name for alias in FreeRiskAPI)]


class FMPToolInput(BaseModel):
    """Input that the LLM must supply to the `fmp_api` function."""

    endpoint: EndpointAlias = Field(  # type: ignore
        ..., description="Alias of an endpoint available on the free/public tier."
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Placeholder parameters used to fill the URL.",
    )


class FMPTool(BaseTool):
    """
    Single tool that lets the LLM call *any* endpoint declared in `FreeRiskAPI`.
    Prevents calls outside the list, appends `apikey`, and handles errors.
    """

    name = "fmp_api"
    description = (
        "Access Financial Modeling Prep. Pick an `endpoint` from FreeRiskAPI "
        "aliases and pass the required `params`. Returns JSON."
    )
    args_schema = FMPToolInput

    client: FMPClient

    async def _arun(self, endpoint: str, params: dict[str, Any]) -> Any:
        api_enum = FreeRiskAPI[endpoint]
        try:
            path = api_enum(**{k: str(v) for k, v in params.items()})
        except KeyError as exc:
            raise ValueError(f"Missing required parameter: {exc}") from None

        return await self.client._fmp_get(path)

    def _run(self, endpoint: str, params: dict[str, Any]) -> Any:
        return asyncio.run(self._arun(endpoint, params))
