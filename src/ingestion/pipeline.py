import logging
import os

from config import Settings
from core.downloader import SECDownloader
from core.ingestor import GraphIngestor
from core.processor import SECProcessor

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    settings = Settings()

    form_types = settings.FORM_TYPES.split(",")

    downloaded_reports = []

    if settings.DOWNLOAD:
        logger.info("🚀 Starting download step...")
        downloader = SECDownloader(root_dir=settings.DATA_DIR)
        downloaded_reports = downloader.fetch_sec_filings(form_types=form_types)
    else:
        logger.info(
            "📦 Skipping download step. Using existing files in data directory..."
        )
        downloaded_reports = []
        for form in form_types:
            form_dir = os.path.join(settings.DATA_DIR, form)
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

    if settings.PROCESS or settings.INGEST:
        logger.info("🧩 Starting processing step...")
        processor = SECProcessor()
        """ingestor = GraphIngestor(
            connection_config={
                "host": settings.GRAPH_HOST,
                "user": settings.GRAPH_USER,
                "password": settings.GRAPH_PASSWORD,
            }
        )"""

        for report in downloaded_reports:
            path = (
                report.local_path
                if hasattr(report, "local_path")
                else report["local_path"]
            )
            company = (
                report.company if hasattr(report, "company") else report["company"]
            )
            if not path:
                continue
            logger.info(f"Processing {path}")
            chunks = processor.process_document(
                path, company=company, year=settings.REPORT_YEAR
            )
            logger.info(f"✔️ Extracted {len(chunks)} chunks from {company}")

            if settings.INGEST:
                pass
                # ingestor.ingest_chunks(chunks)

    logger.info("✅ ETL pipeline finished.")


if __name__ == "__main__":
    main()
