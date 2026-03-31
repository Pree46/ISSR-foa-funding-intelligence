"""Source router — dispatches FOA URL to the correct ingestion module."""

from foa_pipeline.ingest.grants_gov import fetch_grants_gov
from foa_pipeline.ingest.nsf import fetch_nsf
from foa_pipeline.ingest.nih import fetch_nih_project, fetch_nih_by_keyword
from foa_pipeline.utils.logger import get_logger

log = get_logger(__name__)

def ingest(url: str) -> dict:
    """Ingest a single FOA URL and return a normalised record dict.

    Raises ValueError for unsupported domains.
    """
    url_lower = url.lower()
    
    if "grants.gov" in url_lower:
        log.info("Matched source: grants.gov")
        return fetch_grants_gov(url)
    elif "nsf.gov" in url_lower or url_lower.startswith("nsf"):
        log.info("Matched source: nsf.gov")
        return fetch_nsf(url)
    elif url.upper().startswith("R") and len(url) > 1 and (url[1].isdigit() or url[1].upper() in "ABCDEFGHIJ"):
        log.info("Matched source: NIH Project")
        return fetch_nih_project(url)
    elif any(kw in url_lower for kw in ["nih", "niaid", "nccr", "ninds"]):
        log.info("Matched source: NIH Keyword")
        return fetch_nih_by_keyword(url)

    supported = "NSF, Grants.gov, NIH"
    raise ValueError(
        f"Unsupported FOA source. Provide a URL/ID from one of: {supported}\n"
        f"Got: {url}"
    )
