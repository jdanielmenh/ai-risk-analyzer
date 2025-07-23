import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

REQUIRED_ENV_VARS = (
    "OPENAI_API_KEY",
    "LANGSMITH_API_KEY",
    "LANGSMITH_TRACING",
    "LANGSMITH_ENDPOINT",
    "LANGSMITH_PROJECT",
)
if not all(var in os.environ for var in REQUIRED_ENV_VARS):
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)


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
    news_api_key: str
    fmp_api_key: str
    http_timeout: int = 10

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


class LLMSettings(BaseSettings):
    """Settings for the OpenAI chat model used across the project."""

    openai_api_key: str = Field(description="API key for OpenAI access")
    openai_model: str = Field("gpt-4o-mini", description="OpenAI model name")
    openai_temperature: float = Field(0.0, description="Sampling temperature")
    openai_max_tokens: int | None = Field(
        default=None, description="Hard limit on tokens to generate"
    )
    openai_request_timeout: int = Field(
        default=60, description="OpenAI request timeout in seconds"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }
