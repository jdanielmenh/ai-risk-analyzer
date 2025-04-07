import logging
import os
import time
from typing import Literal

import httpx
import msgspec
import pandas as pd
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import ingestion.models as models

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# SEC requires an email in the User-Agent
HEADERS = {"User-Agent": "John Doe johndoe@gmail.com"}

# SEC API URLs
SEC_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{}.json"


def get_sp500_companies() -> list[models.SP500Company]:
    """
    Fetches a list of S&P 500 companies as SP500Company objects from Wikipedia.
    Returns: list[SP500Company]
    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        tables = pd.read_html(url)
        df = tables[0][["Symbol", "CIK"]].dropna()

        companies = [
            models.SP500Company(
                ticker=row["Symbol"].replace(".", "-").upper(),
                cik=str(int(row["CIK"])).zfill(10),
            )
            for _, row in df.iterrows()
        ]

        return companies

    except Exception as e:
        logger.error(f"Error fetching S&P 500 companies: {e}")
        return []


def get_latest_filings(cik: str, form_type: str = "10-K") -> str | None:
    """
    Fetch the latest 10-K or 10-Q filing URL for a given company.
    """
    url = SEC_SUBMISSIONS_URL.format(cik)

    try:
        response = httpx.get(url, headers=HEADERS)
        response.raise_for_status()
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch filings for CIK {cik}: {e}")
        return None

    company_filings = msgspec.json.decode(
        response.content, type=models.CompanyFilings, strict=True
    )
    recent_filings = company_filings.filings.recent

    try:
        idx = recent_filings.form.index(form_type)
        accession_number = recent_filings.accessionNumber[idx].replace("-", "")
        filing_href = recent_filings.primaryDocument[idx]
        cik_clean = str(int(cik))
        filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_clean}/{accession_number}/{filing_href}"
        return filing_url
    except ValueError:
        logger.warning(f"No {form_type} filing found for CIK {cik}")
        return None


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    retry=retry_if_exception_type(httpx.RequestError),
    reraise=True,
)
def download_filing(cik, filing_url, company, output_dir):
    """
    Download the filing document and save it locally.
    Retries automatically if the download fails due to network issues.
    """
    if not filing_url:
        logger.warning(f"No filing URL provided for {company} (CIK: {cik})")
        return None

    save_path = os.path.join(output_dir, f"{company}_{filing_url.split('/')[-1]}")

    response = httpx.get(filing_url, headers=HEADERS)
    response.raise_for_status()

    with open(save_path, "wb") as f:
        f.write(response.content)

    logger.info(f"Filing for {company} (CIK: {cik}) saved to {save_path}")
    return save_path


def fetch_sec_filings(root_dir="data", form_types: list[str] = Literal["10-K", "10-Q"]):
    """
    Fetch and download SEC filings (10-K, 10-Q) for multiple companies.

    Args:
        root_dir (str): Root directory where filings are stored.
        form_types (list[str]): List of form types to fetch (e.g., ["10-K"], ["10-Q"], or ["10-K", "10-Q"]).
    """
    results = {}
    os.makedirs(root_dir, exist_ok=True)
    sp500_companies = get_sp500_companies()

    for company in sp500_companies:
        logger.info(f"Fetching SEC filings for {company.ticker} (CIK: {company.cik})")

        downloaded = {}
        for form_type in form_types:
            filing_url = get_latest_filings(company.cik, form_type=form_type)
            if filing_url:
                # Create a specific subdirectory for each form type
                form_dir = os.path.join(root_dir, form_type)
                os.makedirs(form_dir, exist_ok=True)

                save_path = download_filing(
                    company.cik, filing_url, company.ticker, form_dir
                )
                downloaded[form_type] = save_path
            else:
                logger.warning(f"No {form_type} filing found for {company.ticker}")
                downloaded[form_type] = None

        results[company.ticker] = downloaded

        # Pause to prevent SEC rate-limiting
        time.sleep(6)

    return results


if __name__ == "__main__":
    # Example usage: download only 10-Ks to a custom path
    sec_reports = fetch_sec_filings(root_dir="data", form_types=["10-K"])
    print(sec_reports)
