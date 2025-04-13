from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DOWNLOAD: bool = Field(default=True, description="Download SEC filings")
    PROCESS: bool = Field(default=True, description="Process downloaded filings")
    INGEST: bool = Field(default=True, description="Ingest data into graph DB")
    REPORT_YEAR: int = 2024
    FORM_TYPES: str = "10-K"
    DATA_DIR: str = "data"

    GRAPH_HOST: str = "bolt://localhost:7687"
    GRAPH_USER: str = "neo4j"
    GRAPH_PASSWORD: str = "password"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
