import json
import os
import time

import httpx
import pandas as pd
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import models.ingestion_models as ingestion_models
from utils.logging_utils import setup_logging

logger = setup_logging(__name__)

# SEC requires an email in the User-Agent
HEADERS = {"User-Agent": "John Doe johndoe@gmail.com"}

# SEC API URLs
SEC_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{}.json"


class SECDownloader:
    def __init__(self, root_dir: str = "data"):
        self._root_dir = root_dir
        os.makedirs(self._root_dir, exist_ok=True)

    def get_sp500_companies(self) -> list[ingestion_models.SP500Company]:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        try:
            tables = pd.read_html(url)
            df = tables[0][["Symbol", "CIK"]].dropna()
            companies = [
                ingestion_models.SP500Company(
                    ticker=row["Symbol"].replace(".", "-").upper(),
                    cik=str(int(row["CIK"])).zfill(10),
                )
                for _, row in df.iterrows()
            ]
            return companies
        except Exception as e:
            logger.error(f"Error fetching S&P 500 companies: {e}")
            return []

    def get_latest_filing_url(self, cik: str, form_type: str = "10-K") -> str | None:
        url = SEC_SUBMISSIONS_URL.format(cik)
        try:
            response = httpx.get(url, headers=HEADERS)
            response.raise_for_status()
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch filings for CIK {cik}: {e}")
            return None

        company_filings_data = json.loads(response.content)
        company_filings = ingestion_models.CompanyFilings(**company_filings_data)
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
        wait=wait_exponential(min=4, max=30),
        retry=retry_if_exception_type(httpx.RequestError),
        reraise=True,
    )
    def _download_filing(
        self, cik: str, filing_url: str, company: str, form_type: str
    ) -> str | None:
        if not filing_url:
            return None
        form_dir = os.path.join(self._root_dir, form_type)
        os.makedirs(form_dir, exist_ok=True)
        save_path = os.path.join(form_dir, f"{company}_{filing_url.split('/')[-1]}")
        response = httpx.get(filing_url, headers=HEADERS)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(response.content)
        logger.info(f"Downloaded {form_type} for {company} to {save_path}")
        return save_path

    def fetch_sec_filings(
        self, form_types: list[str], tickers: list[str] | None = None
    ) -> list[ingestion_models.DownloadedReport]:
        reports = []
        companies = self.get_sp500_companies()

        if tickers:
            companies = [
                company
                for company in companies
                if company.ticker.upper() in [t.upper() for t in tickers]
            ]
            logger.info(f"Filtering for tickers: {tickers}")

        for company in companies:
            for form_type in form_types:
                url = self.get_latest_filing_url(company.cik, form_type)
                path = (
                    self._download_filing(company.cik, url, company.ticker, form_type)
                    if url
                    else None
                )
                reports.append(
                    ingestion_models.DownloadedReport(
                        company=company.ticker,
                        cik=company.cik,
                        form_type=form_type,
                        local_path=path,
                    )
                )
                time.sleep(6)
        return reports
