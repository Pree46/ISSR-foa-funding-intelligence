"""Grants.gov FOA ingestion via their REST API."""

import re
from datetime import datetime

from foa_pipeline.utils.http import fetch
from foa_pipeline.utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_opp_id(url: str) -> str:
    """Extract the numeric opportunity ID from a Grants.gov URL.

    Supported URL patterns:
        * https://www.grants.gov/search-results-detail/350693
        * https://www.grants.gov/view-opportunity.html?oppId=350693
    """
    # Try query-parameter form first (?oppId=...)
    match = re.search(r"oppId=(\d+)", url)
    if match:
        return match.group(1)
    # Slug-based form (/search-results-detail/350693)
    match = re.search(r"/(\d{5,})", url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract opportunity ID from Grants.gov URL: {url}")


def _parse_grants_date(raw: str | int | None) -> str:
    """Convert Grants.gov date format (MMDDYYYY) → ISO 8601 (YYYY-MM-DD)."""
    if not raw:
        return ""
    raw = str(raw).strip()
    for fmt in ("%m%d%Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw  # return as-is if nothing matches


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_grants_gov(url: str) -> dict:
    """Fetch and normalise a Grants.gov FOA record.

    Uses the official REST endpoint::

        GET /grantsws/rest/opportunity/details?oppId=<ID>

    Returns a normalised dict matching the FOA schema.
    """
    opp_id = _extract_opp_id(url)
    api_url = f"https://apply07.grants.gov/grantsws/rest/opportunity/details?oppId={opp_id}"
    log.info("Fetching Grants.gov opportunity %s", opp_id)

    data = fetch(api_url, return_json=True)

    synopsis = data.get("synopsis", {})

    # ── Award range ────────────────────────────────────────────────
    award_floor = synopsis.get("awardFloor", "")
    award_ceiling = synopsis.get("awardCeiling", "")
    award_range = ""
    if award_floor or award_ceiling:
        floor_str = f"${int(award_floor):,}" if award_floor else "N/A"
        ceiling_str = f"${int(award_ceiling):,}" if award_ceiling else "N/A"
        award_range = f"{floor_str} – {ceiling_str}"

    # ── Description ────────────────────────────────────────────────
    description = synopsis.get("synopsisDesc", "")
    if not description and data.get("opportunities"):
        description = data["opportunities"][0].get("description", "")
    # Clean HTML if present
    description = re.sub(r"<[^>]+>", " ", description or "")
    description = re.sub(r"\s{2,}", " ", description).strip()

    # ── Eligibility ────────────────────────────────────────────────
    eligibility = synopsis.get("applicantEligibilityDesc", "")
    if not eligibility:
        eligibility = synopsis.get("applicantTypes", "")
    if isinstance(eligibility, list):
        eligibility = "; ".join(str(e) for e in eligibility)

    return {
        "foa_id": synopsis.get("opportunityNumber")
                  or synopsis.get("opportunityId")
                  or f"GRANTS-{opp_id}",
        "title": synopsis.get("opportunityTitle", "").strip(),
        "agency": synopsis.get("agencyName", "").strip(),
        "open_date": _parse_grants_date(synopsis.get("postDate", "")),
        "close_date": _parse_grants_date(synopsis.get("responseDate", "")),
        "eligibility": eligibility.strip() if isinstance(eligibility, str) else eligibility,
        "description": description[:5000],
        "award_range": award_range,
        "source_url": url,
        "source": "grants.gov",
    }
