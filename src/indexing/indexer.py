"""Vector indexer for managing the indexing process."""

from __future__ import annotations

from neo4j import Driver, GraphDatabase

from indexing.embedder import get_default_embeddings
from indexing.vector_store import Neo4jVectorStore
from models.ingestion_models import DocumentChunk
from utils.config import VectorStoreSettings
from utils.logging_utils import setup_logging

logger = setup_logging(__name__)


class VectorIndexer:
    """
    Manages the complete vector indexing process for SEC documents.

    This class coordinates the embedding and indexing of document chunks
    into the Neo4j vector store.
    """

    def __init__(
        self,
        settings: VectorStoreSettings | None = None,
        driver: Driver | None = None,
    ):
        """
        Initialize the vector indexer.

        Args:
            settings: Configuration settings for vector indexing
            driver: Optional Neo4j driver instance
        """
        self.settings = settings or VectorStoreSettings()

        if driver:
            self.driver = driver
        else:
            self.driver = GraphDatabase.driver(
                self.settings.neo4j_uri,
                auth=(self.settings.neo4j_user, self.settings.neo4j_password),
            )

        # Initialize embeddings and vector store
        self.embeddings = get_default_embeddings()
        self.vector_store = Neo4jVectorStore(
            embeddings=self.embeddings,
            settings=self.settings,
            driver=self.driver,
        )

    def create_index(self) -> None:
        """
        Create the vector index in Neo4j.
        """
        logger.info("🔧 Creating vector index...")
        self.vector_store.create_index()
        logger.info("✅ Vector index creation completed")

    def index_chunks(self, chunks: list[DocumentChunk]) -> list[str]:
        """
        Index a list of document chunks.

        Args:
            chunks: List of DocumentChunk objects to index

        Returns:
            List of document IDs that were indexed
        """
        if not chunks:
            logger.warning("No chunks provided for indexing")
            return []

        logger.info(f"🚀 Starting indexing of {len(chunks)} chunks...")

        # Create index if it doesn't exist
        self.create_index()

        # Add chunks to vector store
        doc_ids = self.vector_store.add_chunks(chunks)

        logger.info(f"✅ Successfully indexed {len(doc_ids)} chunks")
        return doc_ids

    def reindex_all(self, chunks: list[DocumentChunk]) -> list[str]:
        """
        Delete existing index and reindex all chunks.

        Args:
            chunks: List of DocumentChunk objects to index

        Returns:
            List of document IDs that were indexed
        """
        logger.info("🔄 Starting full reindexing...")

        # Delete existing documents
        deleted_count = self.vector_store.delete_all_documents()
        logger.info(f"Deleted {deleted_count} existing documents")

        # Index new chunks
        return self.index_chunks(chunks)

    def get_stats(self) -> dict[str, any]:
        """
        Get indexing statistics.

        Returns:
            Dictionary with indexing statistics
        """
        return self.vector_store.get_index_stats()

    def search(
        self,
        query: str,
        k: int = 5,
        company: str | None = None,
    ) -> list[dict[str, any]]:
        """
        Search the vector index.

        Args:
            query: Search query
            k: Number of results to return
            company: Optional company filter

        Returns:
            List of search results with metadata
        """
        if company:
            documents = self.vector_store.search_by_company(query, company, k)
        else:
            documents = self.vector_store.similarity_search(query, k)

        # Convert to dictionary format for easier handling
        results = []
        for doc in documents:
            result = {
                "content": doc.page_content,
                "metadata": doc.metadata,
            }
            results.append(result)

        return results

    def close(self):
        """Close database connections."""
        if self.vector_store:
            self.vector_store.close()
        if self.driver:
            self.driver.close()


def create_vector_indexer(
    settings: VectorStoreSettings | None = None,
    driver: Driver | None = None,
) -> VectorIndexer:
    """
    Factory function to create a VectorIndexer instance.

    Args:
        settings: Optional vector store settings
        driver: Optional Neo4j driver

    Returns:
        Configured VectorIndexer instance
    """
    return VectorIndexer(settings=settings, driver=driver)
