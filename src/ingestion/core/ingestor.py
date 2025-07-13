from neo4j import Driver

from models.ingestion_models import DocumentChunk
from src.utils import IngestionSettings

settings = IngestionSettings()


class GraphIngestor:
    def __init__(self, driver: Driver):
        self.driver = driver

    def ingest_chunks(self, chunks: list[DocumentChunk]):
        with self.driver.session() as session:
            for chunk in chunks:
                metadata = chunk.metadata
                session.execute_write(
                    self._create_chunk_with_hierarchy,
                    metadata.company,
                    metadata.year,
                    metadata.source,
                    metadata.item,
                    metadata.title,
                    metadata.chunk_id,
                    chunk.text,
                )

    @staticmethod
    def _create_chunk_with_hierarchy(
        tx, company, year, source, item_number, section_title, chunk_id, text
    ):
        tx.run(
            """
            MERGE (c:Company {name: $company})
            MERGE (r:Report {year: $year, source: $source})
            MERGE (c)-[:PUBLISHED]->(r)
            MERGE (s:Section {item_number: $item_number, title: $section_title})
            MERGE (r)-[:CONTAINS]->(s)
            MERGE (ch:Chunk {chunk_id: $chunk_id, text: $text})
            MERGE (s)-[:HAS_CHUNK]->(ch)
            """,
            company=company,
            year=year,
            source=source,
            item_number=item_number,
            section_title=section_title,
            chunk_id=chunk_id,
            text=text,
        )
