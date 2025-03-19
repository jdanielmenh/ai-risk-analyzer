from pydantic import BaseModel

# User Query Model
class SearchRequest(BaseModel):
    query: str

# Response Model
class SearchResult(BaseModel):
    document_id: str
    score: float
    content: str