from ingestion.models.ingestion_models import (
    DocumentChunk,
)


class GraphIngestor:
    def __init__(self, connection_config: dict):
        self.client = self._connect(connection_config)

    def _connect(self, config: dict):
        raise NotImplementedError(
            "Ingesting chunks to graph database is not implemented yet."
        )

    def ingest_chunks(self, chunks: list[DocumentChunk]):
        raise NotImplementedError(
            "Ingesting chunks to graph database is not implemented yet."
        )
