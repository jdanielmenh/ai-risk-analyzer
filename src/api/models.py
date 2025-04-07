import msgspec


class SearchRequest(msgspec.Struct):
    """Search request model."""

    query: str


class SearchResult(msgspec.Struct):
    """Search result model."""

    document_id: str
    score: float
    content: str
