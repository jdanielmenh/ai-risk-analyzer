from pydantic import BaseModel


class SP500Company(BaseModel):
    ticker: str
    cik: int


class RecentFilings(BaseModel):
    form: list[str]
    accessionNumber: list[str]
    primaryDocument: list[str]


class Filings(BaseModel):
    recent: RecentFilings


class CompanyFilings(BaseModel):
    filings: Filings


class DownloadedReport(BaseModel):
    company: str
    cik: str
    form_type: str
    local_path: str | None = None


class TableOfContentsItem(BaseModel):
    item_number: str
    title: str
    anchor_text: str | None


class Section(BaseModel):
    item_number: str
    title: str
    content: str


class ChunkMetadata(BaseModel):
    company: str
    year: int
    item: str
    title: str
    chunk_id: int
    source: str


class DocumentChunk(BaseModel):
    text: str
    metadata: ChunkMetadata
