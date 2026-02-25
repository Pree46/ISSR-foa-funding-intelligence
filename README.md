# FOA Funding Intelligence Pipeline

A lightweight, modular pipeline that ingests Funding Opportunity Announcements (FOAs) from **Grants.gov** and **NSF**, extracts structured fields, applies rule-based semantic tags, and exports clean `foa.json` and `foa.csv` files.

---

## Quickstart

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the pipeline
```bash
python main.py --url "<FOA_URL>" --out_dir ./out
```

**Examples:**
```bash
# Grants.gov
python main.py --url "https://www.grants.gov/search-results-detail/350693" --out_dir ./out

# NSF
python main.py --url "https://www.nsf.gov/funding/opportunities/artificial-intelligence-research-institutes" --out_dir ./out
```

---

## Output Files

| File | Description |
|---|---|
| `out/foa.json` | Full structured record with nested tags |
| `out/foa.csv` | Flat single-row CSV with tag columns |

---

## Schema

```json
{
  "foa_id":      "unique identifier",
  "title":       "opportunity title",
  "agency":      "funding agency name",
  "open_date":   "YYYY-MM-DD",
  "close_date":  "YYYY-MM-DD",
  "eligibility": "eligibility description",
  "description": "program description",
  "award_range": "$min - $max",
  "source_url":  "original URL",
  "tags": {
    "research_domains": ["machine_learning", "public_health", ...],
    "methods":          ["computational", ...],
    "populations":      ["underserved", ...],
    "sponsor_themes":   ["basic_research", ...]
  }
}
```

---

## Condition Logic (Source Detection)

The pipeline auto-detects the source from the URL:

| URL contains | Module used |
|---|---|
| `grants.gov` | Grants.gov REST API (`/grantsws/rest/opportunity/details`) |
| `nsf.gov` | BeautifulSoup HTML scraper |

No manual source selection needed.

---

## Semantic Tagging

Tags are applied using a **rule-based keyword ontology** across 4 categories:
- `research_domains` — e.g. machine_learning, public_health, education
- `methods` — e.g. computational, experimental, survey_qualitative
- `populations` — e.g. youth, underserved, elderly
- `sponsor_themes` — e.g. innovation, workforce_development, basic_research

The ontology is defined in `main.py` and is easily extensible.

---

## Project Structure

```
main.py           ← pipeline script
requirements.txt  ← dependencies
README.md         ← this file
out/
  foa.json        ← structured output
  foa.csv         ← flat export
```
