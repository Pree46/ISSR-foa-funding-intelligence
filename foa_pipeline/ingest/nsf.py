"""NSF FOA ingestion via HTML scraping of new.nsf.gov."""

import re
from datetime import datetime

from bs4 import BeautifulSoup

from foa_pipeline.utils.http import fetch
from foa_pipeline.utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Date normalisation
# ---------------------------------------------------------------------------

_DATE_FORMATS = [
    "%B %d, %Y",       # January 15, 2024
    "%b %d, %Y",       # Jan 15, 2024
    "%m/%d/%Y",         # 01/15/2024
    "%m-%d-%Y",         # 01-15-2024
    "%Y-%m-%d",         # 2024-01-15  (already ISO)
    "%d %B %Y",         # 15 January 2024
    "%B %Y",            # January 2024
]


def _normalise_date(raw: str) -> str:
    """Best-effort date normalisation → ISO 8601 (YYYY-MM-DD)."""
    if not raw:
        return ""
    cleaned = raw.strip().rstrip(".")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Try regex for embedded dates like "Due October 09, 2024"
    m = re.search(
        r"(\w+ \d{1,2},?\s*\d{4})", cleaned
    )
    if m:
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(m.group(1), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return cleaned  # return as-is


# ---------------------------------------------------------------------------
# HTML extraction helpers
# ---------------------------------------------------------------------------

def _get_text(soup: BeautifulSoup, selector: str) -> str:
    el = soup.select_one(selector)
    return el.get_text(separator=" ", strip=True) if el else ""


def _find_field_by_labels(soup: BeautifulSoup, labels: list[str]) -> str:
    """Search for a field by looking for label-like elements containing any of
    the given strings, then extracting the related value text."""
    for tag in soup.find_all(["dt", "th", "strong", "label", "span", "h3", "h4", "p"]):
        tag_text = tag.get_text().lower().strip()
        for label in labels:
            if label.lower() in tag_text:
                # Try the next-sibling first (common in <dt>/<dd> pairs)
                sibling = tag.find_next_sibling()
                if sibling:
                    txt = sibling.get_text(separator=" ", strip=True)
                    if txt and txt.lower() != tag_text:
                        return txt
                # Fallback: parent minus the label text
                parent = tag.parent
                if parent:
                    full = parent.get_text(separator=" ", strip=True)
                    txt = full.replace(tag.get_text(strip=True), "").strip()
                    if txt:
                        return txt
    return ""


def _extract_nsf_id(soup: BeautifulSoup, url: str) -> str:
    """Extract the NSF solicitation ID (e.g. 'NSF 24-591') from the page.

    Strategy (in order of reliability):
    1. Breadcrumb path (often contains "NSF XX-XXX")
    2. Page text matching the pattern
    3. URL-based fallback
    """
    # Strategy 1: breadcrumb / meta
    page_text = soup.get_text(" ", strip=True)
    nsf_pattern = re.search(r"(NSF\s*\d{2}-\d{3,4})", page_text)
    if nsf_pattern:
        return nsf_pattern.group(1).replace("  ", " ")

    # Strategy 2: solicitation number from URL path
    # e.g.  /funding/opportunities/.../504952/nsf23-576/solicitation
    m = re.search(r"(nsf\d{2}[-]?\d{3,4})", url, re.IGNORECASE)
    if m:
        raw = m.group(1).upper()
        return re.sub(r"(NSF)(\d)", r"\1 \2", raw).replace("-", "-")

    # Strategy 3: numeric ID from URL
    m = re.search(r"/(\d{5,})", url)
    if m:
        return f"NSF-{m.group(1)}"

    return "NSF-UNKNOWN"


def _extract_description(soup: BeautifulSoup) -> str:
    """Extract the main programme description / synopsis."""
    # Look for a Synopsis heading first
    for heading in soup.find_all(["h2", "h3"]):
        if "synopsis" in heading.get_text().lower():
            desc_parts = []
            for sib in heading.find_next_siblings():
                if sib.name in ("h2", "h3"):
                    break
                desc_parts.append(sib.get_text(separator=" ", strip=True))
            combined = " ".join(desc_parts).strip()
            if combined:
                return combined[:5000]

    # Fallback selectors for older NSF page layouts
    for selector in [
        "div.field--name-body",
        "div#synopsis",
        "div.view-mode-full",
        "article",
        "main",
    ]:
        el = soup.select_one(selector)
        if el:
            return el.get_text(separator=" ", strip=True)[:5000]

    return ""


def _extract_eligibility(soup: BeautifulSoup) -> str:
    """Extract eligibility / 'who may submit' information."""
    # Look for "Who May Submit" or "Eligibility" headings
    for heading in soup.find_all(["h2", "h3", "h4", "strong"]):
        heading_text = heading.get_text().lower()
        if any(kw in heading_text for kw in ["who may submit", "eligib"]):
            parts = []
            for sib in heading.find_next_siblings():
                if sib.name in ("h2", "h3", "h4"):
                    break
                parts.append(sib.get_text(separator=" ", strip=True))
            combined = " ".join(parts).strip()
            if combined:
                return combined[:2000]

    # Label-based fallback
    return _find_field_by_labels(soup, ["eligib", "who may submit"])


def _extract_dates(soup: BeautifulSoup) -> tuple[str, str]:
    """Extract open and close dates."""
    # NSF pages often have deadline tables or labeled spans
    open_raw = _find_field_by_labels(
        soup, ["posted date", "open date", "start date", "release date"]
    )
    close_raw = _find_field_by_labels(
        soup, [
            "deadline", "due date", "close date", "full proposal deadline",
            "proposal due", "submission deadline",
        ]
    )
    return _normalise_date(open_raw), _normalise_date(close_raw)


def _extract_award_range(soup: BeautifulSoup) -> str:
    """Extract anticipated funding amount / award range."""
    raw = _find_field_by_labels(
        soup, [
            "anticipated funding", "estimated total", "award amount",
            "funding amount", "anticipated award", "award range",
            "estimated number of awards",
        ]
    )
    return raw[:500] if raw else ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_nsf(url: str) -> dict:
    """Scrape an NSF funding opportunity page and return a normalised FOA record.

    Works with both legacy (www.nsf.gov) and redesigned (new.nsf.gov) pages.
    """
    if not url.startswith("http"):
        url = f"https://www.nsf.gov/cgi-bin/getpub?{url}"
        log.info("Converted solicitation number to URL.")
        
    log.info("Scraping NSF page: %s", url)
    resp = fetch(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Title
    title = (
        _get_text(soup, "h1.page-title")
        or _get_text(soup, "h1")
        or _get_text(soup, "title")
    )

    foa_id = _extract_nsf_id(soup, url)
    description = _extract_description(soup)
    eligibility = _extract_eligibility(soup)
    open_date, close_date = _extract_dates(soup)
    award_range = _extract_award_range(soup)

    # Determine agency sub-organisation if possible
    agency = "National Science Foundation (NSF)"
    org_section = _find_field_by_labels(soup, ["organization", "directorate", "division"])
    if org_section:
        agency += f" — {org_section[:120]}"

    return {
        "foa_id": foa_id,
        "title": title,
        "agency": agency,
        "open_date": open_date,
        "close_date": close_date,
        "eligibility": eligibility,
        "description": description,
        "award_range": award_range,
        "source_url": url,
        "source": "nsf.gov",
    }
