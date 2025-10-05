import logging
import os

from neo4j import GraphDatabase

from indexing.indexer import create_vector_indexer
from ingestion.core.downloader import SECDownloader
from ingestion.core.ingestor import GraphIngestor
from ingestion.core.processor import SECProcessor
from utils.config import IngestionSettings, VectorStoreSettings, load_required_env_vars
from utils.logging_utils import setup_logging

logger = setup_logging(__name__)


def main():
    load_required_env_vars()

    settings = IngestionSettings()
    vector_settings = VectorStoreSettings()
    form_types = settings.form_types.split(",")
    downloaded_reports = []

    if settings.download:
        logger.info("🚀 Starting download step...")
        downloader = SECDownloader(root_dir=settings.data_dir)
        downloaded_reports = downloader.fetch_sec_filings(
            form_types=form_types, tickers=["AAPL", "QCOM", "BAC"]
        )
    else:
        logger.info(
            "📦 Skipping download step. Using existing files in data directory..."
        )
        for form in form_types:
            form_dir = os.path.join(settings.data_dir, form)
            if not os.path.isdir(form_dir):
                continue
            for file in os.listdir(form_dir):
                if file.endswith(".htm"):
                    ticker = file.split("_")[0]
                    downloaded_reports.append(
                        {
                            "company": ticker,
                            "cik": "",
                            "form_type": form,
                            "local_path": os.path.join(form_dir, file),
                        }
                    )

    if settings.process or settings.ingest:
        logger.info("🧩 Starting processing step...")
        processor = SECProcessor()

        driver = GraphDatabase.driver(
            settings.graph_host, auth=(settings.graph_user, settings.graph_password)
        )
        ingestor = GraphIngestor(driver)

        # Initialize vector indexer
        vector_indexer = create_vector_indexer(settings=vector_settings, driver=driver)
        all_chunks = []

        for report in downloaded_reports:
            path = report["local_path"]
            company = report["company"]
            if not path:
                continue
            logger.info(f"Processing {path}")
            chunks = processor.process_document(
                path, company=company, year=settings.report_year
            )
            logger.info(f"✔️ Extracted {len(chunks)} chunks from {company}")
            all_chunks.extend(chunks)

            if settings.ingest:
                ingestor.ingest_chunks(chunks)
                logging.info(
                    f"✔️ Ingested {len(chunks)} chunks into the graph database."
                )

        # Vector indexing step
        if all_chunks:
            logger.info("🔍 Starting vector indexing...")
            vector_indexer.index_chunks(all_chunks)

            # Show indexing stats
            stats = vector_indexer.get_stats()
            logger.info(f"📊 Vector index stats: {stats}")

        # Cleanup
        vector_indexer.close()
        driver.close()

    logger.info("✅ ETL pipeline finished.")


if __name__ == "__main__":
    main()
