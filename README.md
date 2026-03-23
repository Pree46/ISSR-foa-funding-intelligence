# FOA Funding Intelligence Pipeline

> A modular semantic tagging engine for ingesting, processing, and analyzing **Funding Opportunity Announcements (FOAs)** from NSF, NIH, and Grants.gov — built for the ISSR · University of Alabama
> 
> **Part of Google Summer of Code (GSoC) 2026**
<p align="center">
  <img src="https://humanai.foundation/images/humanai.jpg" alt="humanai" width="120" height="120"/>
  <img src="https://humanai.foundation/images/GSoC/GSoC-icon-192.png" alt="gsoc" width="120" height="120"/>
</p>
---

## Background

Funding opportunity announcements contain rich structured data — eligibility, award ranges, research domains, target populations, and sponsor priorities. Yet researchers manually sift through hundreds of FOAs to find matches for their expertise and interests. 

This project provides an automated, extensible pipeline to ingest FOAs from multiple agencies, apply **hybrid semantic tagging** (rule-based keywords + sentence-transformers embeddings), and export structured data ready for research or deployment. The system is designed for reuse: define new agencies, ontology terms, or tagging strategies in configuration and deploy without backend changes.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Multi-source ingestion** | NSF (HTML), NIH (Federal Reporter API), Grants.gov (REST) |
| **Hybrid semantic tagging** | Rule-based keywords + embedding-based semantic similarity (sentence-transformers) |
| **Configurable ontology** | 22 terms across 4 categories (research domains, methods, populations, sponsor themes) |
| **Evaluation framework** | Precision/recall metrics on hand-labeled test set (6 FOAs) |
| **Dual export** | Structured JSON and flat-file CSV output |
| **High modularity** | Pluggable ingestion modules; configure via Python dicts |

---

## Quick Start

### 1. Install
```bash
pip install -r requirements.txt
```

### 2. Ingest a FOA
```bash
# NSF (solicitation number)
python main.py --url "nsf24520" --out_dir ./out --hybrid

# NIH (grant number or keyword)
python main.py --url "R01CA123456" --out_dir ./out

# Grants.gov (full URL)
python main.py --url "https://www.grants.gov/search-results-detail/350693" --out_dir ./out
```

### 3. Evaluate on test set
```bash
python main.py --eval evaluation_dataset.json --eval_out results.json
```

---

## Ingestion Sources

| Agency | Input Format | Example | API | Status |
|--------|--------------|---------|-----|--------|
| **NSF** | Solicitation number or CGI-BIN URL | `nsf24520` | BeautifulSoup HTML parser | ✓ Working |
| **NIH** | Grant ID or keyword | `R01CA123456` | Federal Reporter v2 (public) | ✓ Working |
| **Grants.gov** | Opportunity URL | `https://grants.gov/...` | REST API | ⚠ Auth wall |

---

## Output Schema

```json
{
  "foa_id": "NSF-24-520",
  "title": "NSF 24-520: Long-Term Ecological Research (LTER)",
  "agency": "National Science Foundation (NSF)",
  "open_date": "2023-12-21",
  "close_date": "2024-03-14",
  "award_range": "$15.3M",
  "description": "Program focuses on...",
  "tags": {
    "research_domains": ["environment", "data_science"],
    "methods": ["experimental", "computational"],
    "populations": ["general_public"],
    "sponsor_themes": ["basic_research"]
  },
  "source_url": "https://www.nsf.gov/cgi-bin/getpub?nsf24520"
}
```

---

## Hybrid Semantic Tagging

Two-signal approach:

1. **Rule-based** — Fast keyword matching against ontology (4 categories × 22 terms)
2. **Embedding-based** — Cosine similarity via sentence-transformers (`all-MiniLM-L6-v2`)
3. **Hybrid score** — Weighted combination: `0.4 × keyword_score + 0.6 × embedding_score`

Thresholds and weights configurable in [tagger_hybrid.py](tagger_hybrid.py#L40). Default: `embedding_threshold=0.5`, `rule_weight=0.4`.

---

## Project Structure

```
FOA Funding Intelligence/
├── main.py                    # CLI entry point + router
├── tagger_hybrid.py           # Hybrid semantic tagger
├── ingest_nih.py              # NIH Federal Reporter integration
├── evaluator.py               # Precision/recall evaluation
├── evaluation_dataset.json    # 6 hand-labeled FOAs (test set)
├── requirements.txt
└── README.md
```

---

## Evaluation Results

Hand-labeled dataset: **6 diverse FOAs** across NSF and NIH

| Metric | Value | Notes |
|--------|-------|-------|
| **Precision** | 1.000 | No false positives |
| **Recall** | 0.045 | Conservative thresholds; recommend lowering to 0.3–0.4 for production |
| **F1-Score** | 0.087 | Best category: research_domains (F1=0.31) |

See [TESTING_REPORT.md](TESTING_REPORT.md) for per-category breakdown.

---

## How to Run Locally

### Prerequisites
- Python 3.8+

### Setup
```bash
git clone https://github.com/Pree46/foa-funding-intelligence.git
cd foa-funding-intelligence
pip install -r requirements.txt
```

### Commands

| Command | Purpose |
|---------|---------|
| `python main.py --url "nsf24520" --out_dir ./out` | Ingest NSF FOA |
| `python main.py --url "nsf24520" --out_dir ./out --legacy` | Use rule-based tagging only |
| `python main.py --eval evaluation_dataset.json --eval_out results.json` | Run evaluation |

Outputs: `foa.json`, `foa.csv`

---

## Task Domains Covered

Evaluation dataset spans 3 domains at 2 stakes levels to test generalization:

| Domain | Stakes | Examples |
|--------|--------|----------|
| Medical | High | Patient review, clinical research |
| Finance | High | Loan assessment, risk analysis |
| Everday/Consumer | Low | Laptop comparison, plan selection |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Language** | Python 3.8+ |
| **Web scraping** | BeautifulSoup4, requests |
| **Semantic embeddings** | sentence-transformers (all-MiniLM-L6-v2) |
| **Evaluation** | scikit-learn (precision/recall/F1) |
| **Data storage** | Flat-file JSON + CSV |
| **Analysis** | Jupyter, pandas, matplotlib |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| NSF returns 404 | Use CGI-BIN format: `https://www.nsf.gov/cgi-bin/getpub?nsf24520` |
| Grants.gov authentication | Known limitation; use NSF/NIH instead |
| NIH project not found | Verify format `R01CA123456` or try keyword search |
| Tags empty | Lower threshold in [tagger_hybrid.py](tagger_hybrid.py#L40) from 0.5 → 0.3 |

---

## Future Work

- [ ] Expand test set to 20+ FOAs
- [ ] Fine-tune embeddings on funding domain text
- [ ] Add vector indexing (FAISS) for semantic search
- [ ] Lower thresholds for production deployment
- [ ] LLM-assisted disambiguation for ambiguous cases

---

## Contact

**Mentors:**
- Andrya Allen (University of Alabama)
- Dr. Xinyue Ye (University of Alabama)  
- Dr. Andrea Underhill (University of Alabama)

**Last Updated:** March 23, 2026  

