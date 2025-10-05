import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

from utils.logging_utils import setup_logging

logger = setup_logging(__name__)

REQUIRED_ENV_VARS = (
    "OPENAI_API_KEY",
    "LANGSMITH_API_KEY",
    "LANGSMITH_TRACING",
    "LANGSMITH_ENDPOINT",
    "LANGSMITH_PROJECT",
    "LANGSMITH_TEST_TRACKING",
)


def load_required_env_vars() -> None:
    if not all(var in os.environ for var in REQUIRED_ENV_VARS):
        env_path = Path(__file__).resolve().parents[2] / ".env"
        logger.debug(f"Loading environment variables from {env_path}")
        if env_path.exists():
            load_dotenv(env_path)

        missing = [var for var in REQUIRED_ENV_VARS if var not in os.environ]
        if missing:
            logger.warning(
                "The following required environment variables are still missing: "
                + ", ".join(missing)
            )
    else:
        logger.debug("All required environment variables are already present.")


class IngestionSettings(BaseSettings):
    download: bool = Field(default=True, description="Download SEC filings")
    process: bool = Field(default=True, description="Process downloaded filings")
    ingest: bool = Field(default=True, description="Ingest data into graph DB")
    report_year: int = 2024
    form_types: str = "10-K"
    data_dir: str = "data"

    graph_host: str = "bolt://localhost:7687"
    graph_user: str = "neo4j"
    graph_password: str = "password"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


class ClientsSettings(BaseSettings):
    fmp_api_key: str
    http_timeout: int = 10

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


class LLMSettings(BaseSettings):
    """Settings for the OpenAI chat model used throughout the project."""

    openai_api_key: str = Field(description="API key for OpenAI access")
    openai_model: str = Field("gpt-4o-mini", description="OpenAI model name")
    openai_temperature: float = Field(0.0, description="Sampling temperature")
    openai_max_tokens: int | None = Field(
        default=None, description="Hard limit on the number of tokens to generate"
    )
    openai_request_timeout: int = Field(
        default=60, description="OpenAI request timeout in seconds"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


class VectorStoreSettings(BaseSettings):
    """Settings for Neo4j vector store and embeddings."""

    # Neo4j connection settings
    neo4j_uri: str = Field("bolt://localhost:7687", description="Neo4j database URI")
    neo4j_user: str = Field("neo4j", description="Neo4j username")
    neo4j_password: str = Field("password", description="Neo4j password")

    # Vector index settings
    vector_index_name: str = Field(
        "sec_documents_vector", description="Name of the vector index"
    )
    document_node_label: str = Field(
        "DocumentChunk", description="Node label for document chunks"
    )
    text_property: str = Field("text", description="Property name for text content")
    embedding_property: str = Field(
        "embedding", description="Property name for embeddings"
    )

    # Embedding settings
    embedding_model: str = Field("openai", description="Embedding model provider")
    openai_embedding_model: str = Field(
        "text-embedding-3-small", description="OpenAI embedding model"
    )
    embedding_chunk_size: int = Field(1000, description="Chunk size for embeddings")

    # Vector search settings
    vector_search_k: int = Field(
        5, description="Default number of results for vector search"
    )

    # Deterministic sections retriever settings (non-vector mode)
    deterministic_sections_mode: bool = Field(
        True,
        description="When true, use deterministic sections retriever from Neo4j instead of vector/BM25",
    )
    deterministic_years_back: int = Field(
        1, description="How many recent 10-K reports to consider (yearsBack)"
    )
    deterministic_sections_k: int = Field(
        3, description="Number of sections/snippets to return per preferred item"
    )
    deterministic_snippet_min: int = Field(
        400, description="Minimum snippet length (characters)"
    )
    deterministic_snippet_max: int = Field(
        600, description="Maximum snippet length (characters)"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_prefix": "VECTOR_",
        "extra": "ignore",
    }
