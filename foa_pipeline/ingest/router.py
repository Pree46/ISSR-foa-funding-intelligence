"""Source router — dispatches FOA URL to the correct ingestion module."""

from foa_pipeline.ingest.grants_gov import fetch_grants_gov
from foa_pipeline.ingest.nsf import fetch_nsf
from foa_pipeline.utils.logger import get_logger

log = get_logger(__name__)

_SOURCE_DISPATCH = [
    ("grants.gov", fetch_grants_gov),
    ("nsf.gov", fetch_nsf),
]


def ingest(url: str) -> dict:
    """Ingest a single FOA URL and return a normalised record dict.

    Raises ValueError for unsupported domains.
    """
    url_lower = url.lower()
    for domain, handler in _SOURCE_DISPATCH:
        if domain in url_lower:
            log.info("Matched source: %s", domain)
            return handler(url)

    supported = ", ".join(d for d, _ in _SOURCE_DISPATCH)
    raise ValueError(
        f"Unsupported FOA source. URL must be from one of: {supported}\n"
        f"Got: {url}"
    )
