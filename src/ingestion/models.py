import msgspec


class SP500Company(msgspec.Struct):
    ticker: str
    cik: int


class RecentFilings(msgspec.Struct):
    form: list[str]
    accessionNumber: list[str]
    primaryDocument: list[str]


class Filings(msgspec.Struct):
    recent: RecentFilings


class CompanyFilings(msgspec.Struct):
    filings: Filings
