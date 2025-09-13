"""Document retriever node for the RiskBot that uses vector search."""

from __future__ import annotations

from indexing.indexer import create_vector_indexer
from riskbot.utils.states import ConversationState
from utils.config import VectorStoreSettings
from utils.logging_utils import setup_logging

logger = setup_logging(__name__)


async def document_retriever_node(state: ConversationState) -> ConversationState:
    """
    Document retriever node that searches for relevant SEC document chunks
    based on the user's question using vector similarity search.

    Assumes the vector index has been created by the ingestion pipeline.
    """
    if not state.execution_plan:
        logger.warning("No execution plan found for document retrieval")
        return state

    try:
        # Initialize vector indexer for search (no index creation here)
        vector_settings = VectorStoreSettings()
        vector_indexer = create_vector_indexer(settings=vector_settings)

        # Extract company symbol from execution plan
        company_symbol = state.execution_plan.company_symbol

        # Perform vector search
        search_results = vector_indexer.search(
            query=state.question,
            k=5,  # Get top 5 most relevant chunks
            company=company_symbol if company_symbol else None,
        )

        # Store search results in state
        if not state.api_results:
            state.api_results = {}

        state.api_results["document_search"] = {
            "query": state.question,
            "company_filter": company_symbol,
            "results": search_results,
            "total_found": len(search_results),
        }

        logger.info(f"Found {len(search_results)} relevant document chunks")

        # Cleanup
        vector_indexer.close()

    except Exception as e:
        # Surface the issue but keep graph execution moving
        logger.error(f"Error in document retrieval: {str(e)}")
        if not state.api_results:
            state.api_results = {}
        state.api_results["document_search"] = {"error": str(e), "results": []}

    return state
