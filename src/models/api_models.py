from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request model."""

    query: str = Field(..., description="The search query string.")


class SearchResult(BaseModel):
    """Search result model."""

    document_id: str
    score: float
    content: str
