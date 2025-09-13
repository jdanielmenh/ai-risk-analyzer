"""Neo4j vector store implementation using LangChain Neo4jVector."""

from __future__ import annotations

from typing import Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_neo4j import Neo4jVector
from neo4j import Driver, GraphDatabase

from models.ingestion_models import DocumentChunk
from utils.config import VectorStoreSettings
from utils.logging_utils import setup_logging

logger = setup_logging(__name__)


class Neo4jVectorStore:
    """
    Wrapper around LangChain Neo4jVector for SEC document indexing.

    This class manages the creation and interaction with Neo4j vector indices
    for semantic search over SEC document chunks.
    """

    def __init__(
        self,
        embeddings: Embeddings,
        settings: VectorStoreSettings | None = None,
        driver: Driver | None = None,
    ):
        """
        Initialize the Neo4j vector store.

        Args:
            embeddings: Embeddings model to use for vectorization
            settings: Configuration settings for the vector store
            driver: Optional Neo4j driver instance
        """
        self.settings = settings or VectorStoreSettings()
        self.embeddings = embeddings

        if driver:
            self.driver = driver
        else:
            self.driver = GraphDatabase.driver(
                self.settings.neo4j_uri,
                auth=(self.settings.neo4j_user, self.settings.neo4j_password),
            )

        self._vector_store: Neo4jVector | None = None

    def _get_vector_store(self) -> Neo4jVector:
        """Get or create the Neo4jVector instance."""
        if self._vector_store is None:
            self._vector_store = Neo4jVector(
                embedding=self.embeddings,
                url=self.settings.neo4j_uri,
                username=self.settings.neo4j_user,
                password=self.settings.neo4j_password,
                index_name=self.settings.vector_index_name,
                node_label=self.settings.document_node_label,
                text_node_property=self.settings.text_property,
                embedding_node_property=self.settings.embedding_property,
            )
        return self._vector_store

    def create_index(self) -> None:
        """
        Create the vector index in Neo4j if it doesn't exist.
        """
        index_name = self.settings.vector_index_name
        label = self.settings.document_node_label
        embedding_prop = self.settings.embedding_property

        # Check if index exists
        with self.driver.session() as session:
            result = session.run(
                "SHOW INDEXES YIELD name, type WHERE name = $index_name",
                index_name=index_name,
            )
            if result.single():
                logger.info(
                    f"Vector index '{index_name}' already exists; skipping creation"
                )
                return

        # Determine embedding dimension (probe once)
        try:
            dim = len(self.embeddings.embed_query("dimension probe"))
        except Exception as e:
            logger.warning(
                f"Failed to probe embedding dimension ({e}); defaulting to 1536"
            )
            dim = 1536

        logger.info(
            f"Creating vector index '{index_name}' on :{label}({embedding_prop}) with dimension {dim}..."
        )

        # Try older signature first (most common): (name, label, property, dimensions, similarity)
        create_query_legacy = "CALL db.index.vector.createNodeIndex($name, $label, $property, $dimensions, $similarity)"
        params_legacy = {
            "name": index_name,
            "label": label,
            "property": embedding_prop,
            "dimensions": dim,
            "similarity": "cosine",
        }

        # Newer signature variant with config map (fallback)
        create_query_new = (
            "CALL db.index.vector.createNodeIndex($name, $label, $property, $config)"
        )
        params_new = {
            "name": index_name,
            "label": label,
            "property": embedding_prop,
            "config": {"similarity_function": "cosine", "vector_dimension": dim},
        }

        with self.driver.session() as session:
            try:
                session.run(create_query_legacy, **params_legacy).consume()
            except Exception as e1:
                logger.debug(
                    f"Legacy createNodeIndex signature failed: {e1}; trying config map signature"
                )
                try:
                    session.run(create_query_new, **params_new).consume()
                except Exception as e2:
                    logger.error(f"Failed to create vector index '{index_name}': {e2}")
                    raise

            # Verify creation
            verify = session.run(
                "SHOW INDEXES YIELD name, type WHERE name = $index_name",
                index_name=index_name,
            )
            if verify.single():
                logger.info(f"✅ Vector index '{index_name}' created or available")
            else:
                logger.warning(
                    f"⚠️ Vector index '{index_name}' was not found after creation attempt"
                )

    def add_chunks(self, chunks: list[DocumentChunk]) -> list[str]:
        """
        Add document chunks to the vector store.

        Args:
            chunks: List of DocumentChunk objects to index

        Returns:
            List of document IDs that were added
        """
        if not chunks:
            logger.warning("No chunks provided for indexing")
            return []

        # Convert DocumentChunk objects to LangChain Document objects
        documents = []
        for chunk in chunks:
            doc = Document(
                page_content=chunk.text,
                metadata={
                    # Core metadata
                    "company": chunk.metadata.company,
                    "year": chunk.metadata.year,
                    # Map to names used elsewhere in queries/CLI
                    "section_title": chunk.metadata.title,
                    "item_number": chunk.metadata.item,
                    "chunk_index": chunk.metadata.chunk_id,
                    "source_file": chunk.metadata.source,
                    # Keep original names too (optional, for compatibility)
                    "title": chunk.metadata.title,
                    "item": chunk.metadata.item,
                    "chunk_id": chunk.metadata.chunk_id,
                    "source": chunk.metadata.source,
                },
            )
            documents.append(doc)

        logger.info(f"Adding {len(documents)} document chunks to vector store...")

        vector_store = self._get_vector_store()
        doc_ids = vector_store.add_documents(documents)

        logger.info(f"✅ Successfully added {len(doc_ids)} chunks to vector store")
        return doc_ids

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[Document]:
        """
        Perform similarity search on the vector store.

        Args:
            query: Search query text
            k: Number of results to return
            filter_dict: Optional metadata filters

        Returns:
            List of similar documents
        """
        vector_store = self._get_vector_store()

        if filter_dict:
            # Convert filter to Cypher WHERE clause format
            results = vector_store.similarity_search(query, k=k)
            # TODO: Implement proper filtering - Neo4jVector doesn't support filter param directly
            return results
        else:
            return vector_store.similarity_search(query, k=k)

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[tuple[Document, float]]:
        """
        Perform similarity search and return results with similarity scores.

        Args:
            query: Search query text
            k: Number of results to return
            filter_dict: Optional metadata filters

        Returns:
            List of (document, score) tuples
        """
        vector_store = self._get_vector_store()
        return vector_store.similarity_search_with_score(query, k=k)

    def search_by_company(
        self,
        query: str,
        company: str,
        k: int = 5,
    ) -> list[Document]:
        """
        Search for documents from a specific company.

        Args:
            query: Search query text
            company: Company ticker symbol
            k: Number of results to return

        Returns:
            List of documents from the specified company
        """
        # Use Cypher query to filter by company
        # vector_store = self._get_vector_store()

        with self.driver.session() as session:
            # Custom Cypher query for company-specific search
            cypher = f"""
            CALL db.index.vector.queryNodes($index_name, $k, $query_vector)
            YIELD node, score
            WHERE node.company = $company
            RETURN node.{self.settings.text_property} as text,
                   node.company as company,
                   node.year as year,
                   node.section_title as section_title,
                   node.item_number as item_number,
                   score
            ORDER BY score DESC
            LIMIT $k
            """

            # Get query embedding
            query_vector = self.embeddings.embed_query(query)

            result = session.run(
                cypher,
                index_name=self.settings.vector_index_name,
                k=k,
                query_vector=query_vector,
                company=company,
            )

            documents = []
            for record in result:
                doc = Document(
                    page_content=record["text"],
                    metadata={
                        "company": record["company"],
                        "year": record["year"],
                        "section_title": record["section_title"],
                        "item_number": record["item_number"],
                        "score": record["score"],
                    },
                )
                documents.append(doc)

            return documents

    def get_index_stats(self) -> dict[str, Any]:
        """
        Get statistics about the vector index.

        Returns:
            Dictionary with index statistics
        """
        with self.driver.session() as session:
            # Count total documents
            count_result = session.run(
                f"MATCH (n:{self.settings.document_node_label}) RETURN count(n) as total"
            )
            total_docs = count_result.single()["total"]

            # Count by company
            company_result = session.run(
                f"""
                MATCH (n:{self.settings.document_node_label})
                RETURN n.company as company, count(n) as count
                ORDER BY count DESC
                """
            )
            companies = {
                record["company"]: record["count"] for record in company_result
            }

            # Check index existence
            index_result = session.run(
                "SHOW INDEXES YIELD name, type WHERE name = $index_name",
                index_name=self.settings.vector_index_name,
            )
            index_exists = index_result.single() is not None

            return {
                "total_documents": total_docs,
                "companies": companies,
                "index_exists": index_exists,
                "index_name": self.settings.vector_index_name,
            }

    def delete_all_documents(self) -> int:
        """
        Delete all documents from the vector store.

        Returns:
            Number of documents deleted
        """
        with self.driver.session() as session:
            result = session.run(
                f"MATCH (n:{self.settings.document_node_label}) DETACH DELETE n RETURN count(n) as deleted"
            )
            deleted_count = result.single()["deleted"]
            logger.info(f"Deleted {deleted_count} documents from vector store")
            return deleted_count

    def close(self):
        """Close the database connection."""
        if self.driver:
            self.driver.close()
