from collections.abc import Iterable
from typing import Final

_RETRYABLE_STATUS: Final[set[int]] = {429, 500, 502, 503, 504}


class APIError(Exception):
    """
    Base class for all external-API errors raised by this project.

    Attributes
    ----------
    message : str
        Human-readable explanation.
    status  : int | None
        HTTP status code, if available.
    url     : str | None
        Requested URL, useful for logs/metrics.
    """

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        url: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.url = url

    # ---------------------------------------------------------------------
    # Helper utilities
    # ---------------------------------------------------------------------
    def is_retryable(self, extra_status: Iterable[int] | None = None) -> bool:
        """
        Return True if the underlying status code is commonly worth retrying.

        Attributes
        ----------
        extra_status : Iterable[int] | None
            Additional status codes that *you* consider retry-worthy
            (merged with the internal default set).
        """
        if self.status is None:
            return False
        retryable = _RETRYABLE_STATUS | set(extra_status or ())
        return self.status in retryable

    # Nice string representation for logging
    def __str__(self) -> str:  # pragma: no cover
        parts: list[str] = [self.message]
        if self.status is not None:
            parts.append(f"status={self.status}")
        if self.url:
            parts.append(f"url={self.url}")
        return " | ".join(parts)


# -------------------------------------------------------------------------
# Concrete error classes, one per wrapper
# -------------------------------------------------------------------------
class NewsAPIError(APIError):
    """Errors specific to the NewsAPI wrapper."""


class FMPAPIError(APIError):
    """Errors specific to the Financial Modeling Prep wrapper."""
