from pydantic import Field
from pydantic_settings import BaseSettings


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
