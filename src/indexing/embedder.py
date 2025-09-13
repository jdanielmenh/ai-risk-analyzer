"""Document embedder for creating vector representations of text."""

from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from utils.config import VectorStoreSettings
from utils.logging_utils import setup_logging

logger = setup_logging(__name__)


class DocumentEmbedder:
    """
    Handles the creation of embeddings for document chunks.

    This class provides a factory for creating embedding models and utilities
    for working with document embeddings.
    """

    def __init__(self, settings: VectorStoreSettings | None = None):
        """
        Initialize the document embedder.

        Args:
            settings: Configuration settings for embeddings
        """
        self.settings = settings or VectorStoreSettings()

    def get_embeddings(self) -> Embeddings:
        """
        Get the configured embeddings model.

        Returns:
            Embeddings instance configured according to settings
        """
        if self.settings.embedding_model == "openai":
            logger.info(
                f"Creating OpenAI embeddings with model: {self.settings.openai_embedding_model}"
            )
            return OpenAIEmbeddings(
                model=self.settings.openai_embedding_model,
                chunk_size=self.settings.embedding_chunk_size,
            )
        else:
            raise ValueError(
                f"Unsupported embedding model: {self.settings.embedding_model}"
            )

    def embed_text(self, text: str) -> list[float]:
        """
        Create embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Vector representation of the text
        """
        embeddings = self.get_embeddings()
        return embeddings.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Create embeddings for multiple texts.

        Args:
            texts: List of input texts to embed

        Returns:
            List of vector representations
        """
        embeddings = self.get_embeddings()
        return embeddings.embed_documents(texts)

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.

        Returns:
            Dimension of the embedding vectors
        """
        if self.settings.embedding_model == "openai":
            # OpenAI text-embedding-3-small has 1536 dimensions
            # OpenAI text-embedding-3-large has 3072 dimensions
            if "large" in self.settings.openai_embedding_model:
                return 3072
            else:
                return 1536
        else:
            raise ValueError(
                f"Unknown embedding dimension for model: {self.settings.embedding_model}"
            )


@lru_cache(maxsize=1)
def get_default_embedder() -> DocumentEmbedder:
    """
    Get the default document embedder instance.

    Returns:
        Default DocumentEmbedder instance
    """
    return DocumentEmbedder()


@lru_cache(maxsize=1)
def get_default_embeddings() -> Embeddings:
    """
    Get the default embeddings model.

    Returns:
        Default Embeddings instance
    """
    embedder = get_default_embedder()
    return embedder.get_embeddings()
