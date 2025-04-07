from fastapi import APIRouter, HTTPException

from src.api.models import SearchRequest, SearchResult
from src.models.rag.rag_pipeline import RAGPipeline

router = APIRouter()


@router.post("/search", response_model=list[SearchResult])
def search(request: SearchRequest):
    try:
        results = RAGPipeline.run(request.query)
        return results
    except NotImplementedError:
        raise HTTPException(
            status_code=501, detail="Funcion RAG todavia no implementada"
        ) from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
