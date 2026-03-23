"""Rule-based semantic tagger with confidence scoring.

Tags are derived by matching FOA text against the controlled ontology.
Confidence is computed via:
  - keyword hit count
  - title-boost weighting (matches in the title count 3×)
  - negative-keyword suppression
"""

from foa_pipeline.tagging.ontology import ONTOLOGY
from foa_pipeline.utils.logger import get_logger

log = get_logger(__name__)

TITLE_WEIGHT = 3.0   # matches in the title are boosted
MIN_CONFIDENCE = 0.10  # minimum score to keep a tag


def _score_tag(
    keywords: list[str],
    negative: list[str],
    title_lower: str,
    body_lower: str,
) -> float:
    """Compute a confidence score (0.0–1.0) for a single tag."""
    if not keywords:
        return 0.0

    hits = 0
    total_possible = len(keywords) * (1 + TITLE_WEIGHT)  # max if every kw matched title+body

    for kw in keywords:
        in_title = kw in title_lower
        in_body = kw in body_lower
        if in_title:
            hits += TITLE_WEIGHT
        if in_body:
            hits += 1.0

    # Negative keyword suppression
    for neg in negative:
        if neg in body_lower or neg in title_lower:
            hits *= 0.3  # heavy penalty

    score = min(hits / max(total_possible, 1), 1.0)
    return round(score, 3)


def apply_tags(foa: dict) -> dict[str, list[dict]]:
    """Apply semantic tags to an FOA record.

    Parameters
    ----------
    foa : dict
        Normalised FOA record with at least ``title``, ``description``,
        and ``eligibility`` keys.

    Returns
    -------
    dict
        Mapping of category → list of ``{"label": str, "confidence": float}``.
    """
    title_lower = foa.get("title", "").lower()
    body_lower = " ".join([
        foa.get("description", ""),
        foa.get("eligibility", ""),
    ]).lower()

    tags: dict[str, list[dict]] = {}

    for category, labels in ONTOLOGY.items():
        matched = []
        for label, spec in labels.items():
            keywords = spec.get("keywords", [])
            negative = spec.get("negative", [])
            score = _score_tag(keywords, negative, title_lower, body_lower)
            if score >= MIN_CONFIDENCE:
                matched.append({"label": label, "confidence": score})

        # Sort by confidence descending
        matched.sort(key=lambda x: x["confidence"], reverse=True)
        tags[category] = matched

    tag_count = sum(len(v) for v in tags.values())
    log.info("Applied %d tags across %d categories", tag_count, len(tags))
    return tags


def tags_to_flat(tags: dict[str, list[dict]]) -> dict[str, str]:
    """Flatten nested tag structure for CSV export.

    Returns a dict like::

        {"tag_research_domains": "machine_learning (0.85); education (0.42)",
         ...}
    """
    flat = {}
    for category, entries in tags.items():
        parts = [f"{e['label']} ({e['confidence']})" for e in entries]
        flat[f"tag_{category}"] = "; ".join(parts)
    return flat
