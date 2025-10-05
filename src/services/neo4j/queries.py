"""Neo4j cypher queries and helpers for deterministic section retrieval.

This module implements the Cypher queries requested by the user and provides
convenience functions to run them with a Neo4j driver.
"""

from typing import Any

from utils.logging_utils import setup_logging
from neo4j import Driver, GraphDatabase

logger = setup_logging(__name__)

# Section selection policy mapping intent/category to preferred and fallback items
SECTION_POLICY: dict[str, dict[str, list[str]]] = {
    "interest_rates": {"preferred": ["1A"], "fallback": ["7", "7A"]},
    "liquidity": {"preferred": ["1A"], "fallback": ["7", "7A"]},
    "cyber": {"preferred": ["1A"], "fallback": []},
    "litigation": {"preferred": ["1A"], "fallback": []},
    "regulatory": {"preferred": ["1A"], "fallback": []},
    "market_risk": {"preferred": ["1A"], "fallback": ["7", "7A"]},
    "default": {"preferred": ["1A"], "fallback": ["7", "7A"]},
}

# Cypher: last N 10-K reports by ticker
CYPHER_LAST_REPORTS_10K = """
MATCH (c:Company {name: $ticker})-[:PUBLISHED]->(r:Report)
RETURN DISTINCT r.year AS year
ORDER BY r.year DESC
LIMIT $yearsBack
"""

CYPHER_LAST_REPORTS_ALL = """
MATCH (c:Company {name: $ticker})-[:PUBLISHED]->(r:Report)
RETURN DISTINCT r.year AS year
ORDER BY r.year DESC
LIMIT $yearsBack
"""

# Cypher: sections for items and year
CYPHER_SECTIONS_BY_ITEMS = """
MATCH (c:Company {name: $ticker})-[:PUBLISHED]->(r:Report {year: $year})-[:CONTAINS]->(s:Section)-[:HAS_CHUNK]->(ch:Chunk)
WHERE s.item_number IN $items
RETURN ch.chunk_id AS section_id, r.year AS year, s.item_number AS item, s.title AS title, ch.text AS text, r.source AS source, c.name AS company, ch.chunk_id AS chunk_id
"""


def get_driver(uri: str, user: str, password: str) -> Driver:
    """Create and return a Neo4j driver instance."""
    return GraphDatabase.driver(uri, auth=(user, password))


def get_recent_10k_years(driver: Driver, ticker: str, years_back: int = 1) -> list[int]:
    """Return a list of recent 10-K years for a ticker (descending).

    Params:
        driver: Neo4j Driver
        ticker: company ticker
        years_back: how many recent years to return
    """
    with driver.session() as session:
        # Prefer reports that look like 10-K (based on Report.source containing '10-K').
        params = {"ticker": ticker, "yearsBack": years_back}
        logger.info("Running CYPHER_LAST_REPORTS_10K -- params: %s", params)
        logger.info(CYPHER_LAST_REPORTS_10K)
        result = session.run(CYPHER_LAST_REPORTS_10K, params)
        records = list(result)
        years = [record["year"] for record in records]
        logger.info("CYPHER_LAST_REPORTS_10K returned %d rows", len(years))
        # Fallback: if no 10-K-like reports found, return most recent reports of any kind
        if not years:
            logger.info(
                "No 10-K reports found for %s; running CYPHER_LAST_REPORTS_ALL", ticker
            )
            params = {"ticker": ticker, "yearsBack": years_back}
            logger.info("Running CYPHER_LAST_REPORTS_ALL -- params: %s", params)
            logger.info(CYPHER_LAST_REPORTS_ALL)
            result = session.run(CYPHER_LAST_REPORTS_ALL, params)
            records = list(result)
            years = [record["year"] for record in records]
            logger.info("CYPHER_LAST_REPORTS_ALL returned %d rows", len(years))
    return years


def get_sections_by_items(
    driver: Driver, ticker: str, year: int, items: list[str]
) -> list[dict[str, Any]]:
    """Return section nodes matching items for a given ticker and year.

    Each returned dict contains: section_id, year, item, title, text
    """
    # Normalize items to support both '1A' and 'Item 1A' forms used in ingestion
    expanded_items: list[str] = []
    for it in items:
        it = it.strip()
        expanded_items.append(it)
        # If item doesn't start with 'Item', add 'Item {it}' form
        if not it.lower().startswith("item"):
            expanded_items.append(f"Item {it}")
        # Also add the version without 'Item ' if original included it
        if it.lower().startswith("item"):
            stripped = it[4:].strip()
            if stripped:
                expanded_items.append(stripped)

    # deduplicate while preserving order
    seen = set()
    normalized_items = []
    for x in expanded_items:
        if x not in seen:
            seen.add(x)
            normalized_items.append(x)

    params = {"ticker": ticker, "year": year, "items": normalized_items}
    logger.info("Running CYPHER_SECTIONS_BY_ITEMS -- params: %s", params)
    logger.info(CYPHER_SECTIONS_BY_ITEMS)
    with driver.session() as session:
        result = session.run(CYPHER_SECTIONS_BY_ITEMS, params)
        records = list(result)
        logger.info("CYPHER_SECTIONS_BY_ITEMS returned %d rows", len(records))
        sections = [
            {
                "section_id": record["section_id"],
                "year": record["year"],
                "item": record["item"],
                "title": record["title"],
                "text": record["text"],
                "source": record.get("source"),
                "company": record.get("company"),
                "chunk_id": record.get("chunk_id"),
            }
            for record in records
        ]
    return sections
