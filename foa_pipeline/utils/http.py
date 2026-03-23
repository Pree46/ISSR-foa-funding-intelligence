"""HTTP utilities with retry logic and exponential back-off."""

import time
import requests
from foa_pipeline.utils.logger import get_logger

log = get_logger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 (FOA-Pipeline/1.0)"
    )
}


def fetch(
    url: str,
    *,
    headers: dict | None = None,
    timeout: int = 20,
    retries: int = 3,
    backoff: float = 1.5,
    return_json: bool = False,
):
    """Fetch a URL with automatic retries and exponential back-off.

    Parameters
    ----------
    url : str
        Target URL.
    headers : dict, optional
        Extra HTTP headers (merged with defaults).
    timeout : int
        Request timeout in seconds.
    retries : int
        Maximum number of attempts.
    backoff : float
        Back-off multiplier between retries.
    return_json : bool
        If True, parse the response as JSON.

    Returns
    -------
    requests.Response | dict
        Raw response or parsed JSON.
    """
    merged_headers = {**DEFAULT_HEADERS}
    if headers:
        merged_headers.update(headers)

    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            log.info("GET %s (attempt %d/%d)", url, attempt, retries)
            resp = requests.get(url, headers=merged_headers, timeout=timeout)
            resp.raise_for_status()
            return resp.json() if return_json else resp
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < retries:
                wait = backoff ** attempt
                log.warning("Request failed (%s). Retrying in %.1fs…", exc, wait)
                time.sleep(wait)

    raise ConnectionError(
        f"Failed to fetch {url} after {retries} attempts: {last_exc}"
    ) from last_exc
