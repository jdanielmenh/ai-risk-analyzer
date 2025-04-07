import json
import os

import pandas as pd
import pytest

from ingestion.download_sp500_reports import (
    download_filing,
    fetch_sec_filings,
    get_latest_filings,
    get_sp500_companies,
)


# Mock models.SP500Company for testing
class MockSP500Company:
    def __init__(self, ticker, cik):
        self.ticker = ticker
        self.cik = cik


@pytest.fixture
def mock_sp500_companies():
    return [
        MockSP500Company(ticker="AAPL", cik="0000320193"),
        MockSP500Company(ticker="MSFT", cik="0000789019"),
    ]


@pytest.fixture
def mock_read_html(monkeypatch):
    def _mock(url):
        df = pd.DataFrame(
            [
                {"Symbol": "AAPL", "CIK": 320193},
                {"Symbol": "MSFT", "CIK": 789019},
            ]
        )
        return [df]

    monkeypatch.setattr("ingestion.download_sp500_reports.pd.read_html", _mock)


def test_get_sp500_companies(mock_read_html):
    companies = get_sp500_companies()
    assert len(companies) == 2
    assert companies[0].ticker == "AAPL"
    assert companies[0].cik == "0000320193"
    assert companies[1].ticker == "MSFT"
    assert companies[1].cik == "0000789019"


@pytest.fixture
def mock_httpx_get_latest(monkeypatch):
    class MockResponse:
        status_code = 200
        content = json.dumps(
            {
                "filings": {
                    "recent": {
                        "form": ["10-K", "10-Q"],
                        "accessionNumber": [
                            "0000320193-23-000001",
                            "0000320193-23-000002",
                        ],
                        "primaryDocument": ["form10-k.htm", "form10-q.htm"],
                    }
                }
            }
        ).encode()

        def raise_for_status(self):
            pass

    def _mock_get(url, headers=None, timeout=None):
        return MockResponse()

    monkeypatch.setattr("ingestion.download_sp500_reports.httpx.get", _mock_get)


def test_get_latest_filings(mock_httpx_get_latest):
    filing_url = get_latest_filings("0000320193", form_type="10-K")
    assert (
        filing_url
        == "https://www.sec.gov/Archives/edgar/data/320193/000032019323000001/form10-k.htm"
    )


@pytest.fixture
def mock_httpx_get_file(monkeypatch):
    class MockResponse:
        status_code = 200
        content = b"Test content"

        def raise_for_status(self):
            pass

    def _mock_get(url, headers=None, timeout=None):
        return MockResponse()

    monkeypatch.setattr("ingestion.download_sp500_reports.httpx.get", _mock_get)


def test_download_filing(mock_httpx_get_file, tmp_path):
    output_dir = tmp_path / "filings"
    os.makedirs(output_dir, exist_ok=True)

    save_path = download_filing(
        cik="0000320193",
        filing_url="https://www.sec.gov/Archives/edgar/data/320193/000032019323000001/form10-k.htm",
        company="AAPL",
        output_dir=str(output_dir),
    )

    expected_path = output_dir / "AAPL_form10-k.htm"
    assert os.path.exists(expected_path)
    with open(expected_path, "rb") as f:
        content = f.read()
        assert content == b"Test content"
    assert save_path == str(expected_path)


@pytest.fixture
def mock_fetch_sec_deps(monkeypatch, mock_sp500_companies, tmp_path):
    # Mock get_sp500_companies
    monkeypatch.setattr(
        "ingestion.download_sp500_reports.get_sp500_companies",
        lambda: mock_sp500_companies,
    )

    # Mock get_latest_filings
    def _mock_get_latest_filings(cik, form_type):
        if cik == "0000320193" and form_type == "10-K":
            return "https://www.sec.gov/Archives/edgar/data/320193/000032019323000001/form10-k.htm"
        return None

    monkeypatch.setattr(
        "ingestion.download_sp500_reports.get_latest_filings", _mock_get_latest_filings
    )

    # Mock download_filing
    def _mock_download_filing(cik, filing_url, company, output_dir):
        return os.path.join(output_dir, f"{company}_{filing_url.split('/')[-1]}")

    monkeypatch.setattr(
        "ingestion.download_sp500_reports.download_filing", _mock_download_filing
    )

    return tmp_path


def test_fetch_sec_filings(mock_fetch_sec_deps):
    results = fetch_sec_filings(
        root_dir=str(mock_fetch_sec_deps), form_types=["10-K", "10-Q"]
    )

    assert results["AAPL"]["10-K"] == os.path.join(
        str(mock_fetch_sec_deps), "10-K", "AAPL_form10-k.htm"
    )
    assert results["AAPL"]["10-Q"] is None
    assert results["MSFT"]["10-K"] is None
    assert results["MSFT"]["10-Q"] is None
