"""Document retriever node for the RiskBot.

Supports two modes:
- Vector search (default): uses existing vector indexer.
- Deterministic sections mode: queries Neo4j for predefined sections (no BM25/embeddings).
"""

from __future__ import annotations

from indexing.indexer import create_vector_indexer
from riskbot.utils.states import ConversationState
from services.neo4j import queries as neo4j_queries
from utils.config import VectorStoreSettings
from utils.logging_utils import setup_logging

logger = setup_logging(__name__)


def _make_snippets_from_text(
    text: str, k: int, min_len: int, max_len: int
) -> list[str]:
    """Create up to k snippets from text taking slices from the start.

    Simple deterministic strategy: take successive windows from the start, each
    of size between min_len and max_len (prefer max_len), ensuring we don't
    overlap excessively.
    """
    snippets: list[str] = []
    if not text:
        return snippets

    pos = 0
    prefer_len = max_len
    text_len = len(text)
    for _ in range(k):
        if pos >= text_len:
            break
        remaining = text_len - pos
        take = min(prefer_len, remaining)
        # ensure at least min_len if possible
        if take < min_len and remaining >= min_len:
            take = min_len
        snippet = text[pos : pos + take]
        snippets.append(snippet)
        # advance position: non-overlapping windows
        pos += take

    return snippets


async def document_retriever_node(state: ConversationState) -> ConversationState:
    """Retrieve documents either via vector search or deterministic Neo4j sections.

    When deterministic_sections_mode is enabled in config, the node will:
      - map the execution_plan.analysis_focus (intent/category) to preferred
        items using SECTION_POLICY,
      - select the most recent 10-K reports (yearsBack),
      - fetch sections by item for the report year(s),
      - create fixed-length snippets and return traceable evidence.
    """
    if not state.execution_plan:
        logger.warning("No execution plan found for document retrieval")
        return state

    settings = VectorStoreSettings()

    # If deterministic mode is enabled, bypass vector search
    if settings.deterministic_sections_mode:
        try:
            ticker = state.execution_plan.company_symbol
            if not ticker:
                raise ValueError(
                    "No company_symbol in execution plan for deterministic retrieval"
                )

            # Resolve intent/category from execution plan.analysis_focus
            intent = (state.execution_plan.analysis_focus or "").lower()
            policy = neo4j_queries.SECTION_POLICY.get(
                intent, neo4j_queries.SECTION_POLICY.get("default")
            )
            preferred_items = policy.get("preferred", [])
            fallback_items = policy.get("fallback", [])

            # Create neo4j driver
            driver = neo4j_queries.get_driver(
                settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
            )

            years = neo4j_queries.get_recent_10k_years(
                driver, ticker, settings.deterministic_years_back
            )
            evidences = []

            # For each year in priority order, fetch preferred items first
            for year in years:
                # preferred
                if preferred_items:
                    sections = neo4j_queries.get_sections_by_items(
                        driver, ticker, year, preferred_items
                    )
                    for s in sections:
                        snippets = _make_snippets_from_text(
                            s.get("text", ""),
                            settings.deterministic_sections_k,
                            settings.deterministic_snippet_min,
                            settings.deterministic_snippet_max,
                        )
                        for idx, sn in enumerate(snippets):
                            ev = {
                                "source": s.get("source", "neo4j"),
                                "ticker": ticker,
                                "year": year,
                                "section_id": s.get("section_id"),
                                "item": s.get("item"),
                                "title": s.get("title"),
                                "snippet_index": idx,
                                "snippet": sn,
                            }
                            # optional source file
                            if s.get("source_file"):
                                ev["source_file"] = s.get("source_file")
                            evidences.append(ev)

                # if not enough evidence and fallback exists, add fallback sections
                if (
                    fallback_items
                    and len(evidences) < settings.deterministic_sections_k
                ):
                    sections_fb = neo4j_queries.get_sections_by_items(
                        driver, ticker, year, fallback_items
                    )
                    for s in sections_fb:
                        snippets = _make_snippets_from_text(
                            s.get("text", ""),
                            settings.deterministic_sections_k,
                            settings.deterministic_snippet_min,
                            settings.deterministic_snippet_max,
                        )
                        for idx, sn in enumerate(snippets):
                            ev = {
                                "source": s.get("source", "neo4j"),
                                "ticker": ticker,
                                "year": year,
                                "section_id": s.get("section_id"),
                                "item": s.get("item"),
                                "title": s.get("title"),
                                "snippet_index": idx,
                                "snippet": sn,
                            }
                            if s.get("source_file"):
                                ev["source_file"] = s.get("source_file")
                            evidences.append(ev)

            # Close driver
            driver.close()

            if not state.api_results:
                state.api_results = {}

            state.api_results["document_search"] = {
                "mode": "deterministic_sections",
                "query": state.question,
                "company_filter": ticker,
                "years_considered": years,
                "results": evidences,
                "total_found": len(evidences),
            }

            logger.info(
                f"Deterministic retrieval returned {len(evidences)} snippets for {ticker}"
            )

        except Exception as e:
            logger.error(f"Error in deterministic document retrieval: {str(e)}")
            if not state.api_results:
                state.api_results = {}
            state.api_results["document_search"] = {"error": str(e), "results": []}

        return state

    # --- Default: vector search flow ---
    try:
        # Initialize vector indexer for search (no index creation here)
        vector_settings = settings
        vector_indexer = create_vector_indexer(settings=vector_settings)

        # Extract company symbol from execution plan
        company_symbol = state.execution_plan.company_symbol

        # Perform vector search
        search_results = vector_indexer.search(
            query=state.question,
            k=vector_settings.vector_search_k,  # configurable
            company=company_symbol if company_symbol else None,
        )

        # Store search results in state
        if not state.api_results:
            state.api_results = {}

        state.api_results["document_search"] = {
            "mode": "vector",
            "query": state.question,
            "company_filter": company_symbol,
            "results": search_results,
            "total_found": len(search_results),
        }

        logger.info(f"Found {len(search_results)} relevant document chunks (vector)")

        # Cleanup
        vector_indexer.close()

    except Exception as e:
        # Surface the issue but keep graph execution moving
        logger.error(f"Error in document retrieval: {str(e)}")
        if not state.api_results:
            state.api_results = {}
        state.api_results["document_search"] = {"error": str(e), "results": []}

    return state
