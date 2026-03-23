

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# Import hybrid tagger and NIH ingestion
from tagger_hybrid import HybridSemanticTagger, apply_tags as apply_tags_legacy
from ingest_nih import fetch_nih_project, fetch_nih_by_keyword
from evaluator import TaggingEvaluator, load_evaluation_dataset

# Legacy ontology for backward compatibility
ONTOLOGY = {
    "research_domains": {
        "machine_learning":     ["machine learning", "deep learning", "neural network", "artificial intelligence", "ai ", "nlp", "natural language"],
        "public_health":        ["health", "disease", "clinical", "epidemiology", "biomedical", "medicine", "patient", "cancer"],
        "education":            ["education", "learning outcomes", "curriculum", "student", "teacher", "school", "pedagogy"],
        "environment":          ["environment", "climate", "sustainability", "ecology", "carbon", "renewable", "biodiversity"],
        "cybersecurity":        ["cybersecurity", "security", "privacy", "encryption", "network security", "vulnerability"],
        "social_science":       ["social", "behavior", "psychology", "community", "equity", "diversity", "inclusion"],
        "engineering":          ["engineering", "robotics", "manufacturing", "materials", "mechanical", "electrical"],
        "data_science":         ["data science", "big data", "analytics", "visualization", "database", "statistics"],
    },
    "methods": {
        "experimental":         ["experiment", "randomized", "controlled trial", "lab study", "empirical"],
        "computational":        ["computational", "simulation", "modeling", "algorithm", "software"],
        "survey_qualitative":   ["survey", "interview", "qualitative", "ethnograph", "case study", "focus group"],
        "mixed_methods":        ["mixed method", "quantitative and qualitative", "multi-method"],
    },
    "populations": {
        "youth":                ["youth", "children", "adolescent", "K-12", "undergraduate", "student"],
        "underserved":          ["underserved", "underrepresented", "low-income", "minority", "rural", "disadvantaged"],
        "veterans":             ["veteran", "military", "armed forces"],
        "elderly":              ["elderly", "aging", "older adult", "senior"],
        "general_public":       ["public", "community", "citizen", "population"],
    },
    "sponsor_themes": {
        "workforce_development":["workforce", "job training", "career", "employment", "skill development"],
        "innovation":           ["innovation", "entrepreneurship", "startup", "commercialization", "technology transfer"],
        "basic_research":       ["basic research", "fundamental", "discovery", "exploratory"],
        "applied_research":     ["applied research", "translational", "implementation", "deployment"],
        "infrastructure":       ["infrastructure", "facility", "equipment", "instrumentation"],
    }
}


def apply_tags(text: str) -> dict:

    text_lower = text.lower()
    tags = {}
    for category, domains in ONTOLOGY.items():
        matched = []
        for label, keywords in domains.items():
            if any(kw in text_lower for kw in keywords):
                matched.append(label)
        tags[category] = matched
    return tags



def extract_opp_id(url: str):

    match = re.search(r'oppId=(\d+)', url)
    if match:
        return match.group(1)
    match = re.search(r'/(\d{5,})', url)
    if match:
        return match.group(1)
    return None


def fetch_grants_gov(url: str) -> dict:

    opp_id = extract_opp_id(url)
    if not opp_id:
        raise ValueError(f"Could not extract opportunity ID from URL: {url}")

    api_url = f"https://apply07.grants.gov/grantsws/rest/opportunity/details?oppId={opp_id}"
    print(f"[Grants.gov] Fetching opportunity ID: {opp_id}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    
    try:
        resp = requests.get(api_url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        synopsis = data.get("synopsis", {})
        award_floor = synopsis.get("awardFloor", "")
        award_ceiling = synopsis.get("awardCeiling", "")
        award_range = ""
        if award_floor or award_ceiling:
            award_range = f"${award_floor} - ${award_ceiling}"

        def parse_date(d):
            if not d:
                return ""
            try:
                return datetime.strptime(str(d), "%m%d%Y").strftime("%Y-%m-%d")
            except Exception:
                return str(d)

        description = (
            synopsis.get("synopsisDesc", "") or
            data.get("opportunities", [{}])[0].get("description", "") if data.get("opportunities") else ""
        )

        return {
            "foa_id":       synopsis.get("opportunityId") or opp_id,
            "title":        synopsis.get("opportunityTitle", ""),
            "agency":       synopsis.get("agencyName", ""),
            "open_date":    parse_date(synopsis.get("postDate", "")),
            "close_date":   parse_date(synopsis.get("responseDate", "")),
            "eligibility":  synopsis.get("applicantEligibilityDesc", ""),
            "description":  description,
            "award_range":  award_range,
            "source_url":   url,
        }
    except Exception as e:
        print(f"[Grants.gov] API request failed ({e}). Falling back to web scraping...")
        return scrape_grants_gov(url, opp_id)


def scrape_grants_gov(url: str, opp_id: str) -> dict:
    """Fallback scraper for Grants.gov when API is unavailable"""
    print(f"[Grants.gov] Scraping page directly...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        def get_text(selector):
            el = soup.select_one(selector)
            return el.get_text(separator=" ", strip=True) if el else ""

        def find_by_label(label_text):
            for tag in soup.find_all(["dt", "th", "strong", "label"]):
                if label_text.lower() in tag.get_text().lower():
                    sibling = tag.find_next_sibling()
                    if sibling:
                        return sibling.get_text(strip=True)
            return ""

        title = get_text("h1") or get_text("h2") or ""
        description = get_text("div.funded-area") or get_text("div.content") or ""
        
        return {
            "foa_id":       opp_id,
            "title":        title,
            "agency":       find_by_label("agency") or "Unknown",
            "open_date":    find_by_label("open") or "",
            "close_date":   find_by_label("close") or find_by_label("deadline") or "",
            "eligibility":  find_by_label("eligibility") or "",
            "description":  description[:3000],
            "award_range":  find_by_label("award") or "",
            "source_url":   url,
        }
    except Exception as e:
        print(f"[ERROR] Could not scrape Grants.gov: {e}")
        return {
            "foa_id": opp_id,
            "title": "Failed to fetch",
            "agency": "Grants.gov",
            "open_date": "",
            "close_date": "",
            "eligibility": "",
            "description": f"Error fetching data: {str(e)}",
            "award_range": "",
            "source_url": url,
        }

def fetch_nsf(url: str) -> dict:
    """
    Fetch NSF FOA data. Accepts:
    - Full URL: https://www.nsf.gov/cgi-bin/getpub?nsf24520
    - Solicitation number: nsf24520
    """
    
    # Handle solicitation number format (e.g., "nsf24520")
    if not url.startswith("http"):
        url = f"https://www.nsf.gov/cgi-bin/getpub?{url}"
        print(f"[NSF] Converted solicitation number to URL: {url}")
    
    print(f"[NSF] Scraping page: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"[NSF ERROR] URL not found (404): {url}")
        print("[NSF INFO] Use this format:")
        print("[NSF INFO]   - Full URL: https://www.nsf.gov/cgi-bin/getpub?nsf24520")
        print("[NSF INFO]   - Or just: nsf24520 (we'll convert it)")
        raise ValueError(f"Could not access NSF URL.\nError: {e}")
    
    soup = BeautifulSoup(resp.text, "html.parser")

    def get_text(selector):
        el = soup.select_one(selector)
        return el.get_text(separator=" ", strip=True) if el else ""

    def find_by_label(label_text):
        for tag in soup.find_all(["dt", "th", "strong", "label", "span"]):
            if label_text.lower() in tag.get_text().lower():
                sibling = tag.find_next_sibling()
                if sibling:
                    return sibling.get_text(strip=True)
                parent = tag.parent
                if parent:
                    return parent.get_text(strip=True).replace(tag.get_text(), "").strip()
        return ""

    title = (
        get_text("h1.page-title") or
        get_text("h1") or
        get_text("title")
    )

    # Extract FOA ID from title (e.g., "NSF 24-520" from title)
    nsf_id_match = re.search(r'NSF\s*(\d+-\d+)', title)
    if nsf_id_match:
        foa_id = f"NSF-{nsf_id_match.group(1)}"
    else:
        # Fallback: extract from URL parameter
        nsf_id_match = re.search(r'nsf(\d+)', url.lower())
        foa_id = f"NSF-{nsf_id_match.group(1)}" if nsf_id_match else "NSF-UNKNOWN"

    description = ""
    for selector in ["div.field--name-body", "div#synopsis", "div.view-mode-full", "main", "article"]:
        el = soup.select_one(selector)
        if el:
            description = el.get_text(separator=" ", strip=True)[:3000]
            break

    # Extract key information
    open_date = find_by_label("posted") or ""
    
    # Find deadline in description (look for "due by" patterns)
    deadline_match = re.search(r'(?:deadline|due by)\s+([^\n:;]+?)(?:\)|:|,|$)', description, re.IGNORECASE)
    close_date = deadline_match.group(1).strip() if deadline_match else ""

    eligibility = find_by_label("eligib") or ""

    award_range = find_by_label("award") or find_by_label("funding amount") or ""

    return {
        "foa_id":       foa_id,
        "title":        title,
        "agency":       "National Science Foundation (NSF)",
        "open_date":    open_date,
        "close_date":   close_date,
        "eligibility":  eligibility,
        "description":  description,
        "award_range":  award_range,
        "source_url":   url,
    }


def ingest_foa(url: str) -> dict:
    """
    Ingest FOA from multiple sources:
    - NSF: URLs or solicitation numbers (e.g., "nsf24520")
    - Grants.gov: Direct opportunity URLs
    - NIH: Project IDs or keywords (e.g., "R01CA123456")
    """
    if "grants.gov" in url.lower():
        return fetch_grants_gov(url)
    elif "nsf.gov" in url.lower() or url.lower().startswith("nsf"):
        return fetch_nsf(url)
    elif url.upper().startswith("R") and (url[1].isdigit() or url[1].upper() in "ABCDEFGHIJ"):
        # NIH grant number format (R01, R21, etc.)
        return fetch_nih_project(url)
    elif any(kw in url.lower() for kw in ["nih", "niaid", "nccr", "ninds"]):
        # NIH keyword search
        return fetch_nih_by_keyword(url)
    else:
        raise ValueError(
            f"Unsupported source. Provide:\n"
            f"  - NSF: URL or solicitation (nsf24520)\n"
            f"  - Grants.gov: Direct opportunity URL\n"
            f"  - NIH: Grant number (R01CA123456) or keyword\n"
            f"Got: {url}"
        )


def export(record: dict, out_dir: str):

    os.makedirs(out_dir, exist_ok=True)

    # JSON 
    json_path = os.path.join(out_dir, "foa.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    print(f"[Export] JSON saved -> {json_path}")

    # CSV 
    csv_path = os.path.join(out_dir, "foa.csv")
    flat = {k: v for k, v in record.items() if k != "tags"}

    for category, values in record.get("tags", {}).items():
        flat[f"tag_{category}"] = "; ".join(values)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=flat.keys())
        writer.writeheader()
        writer.writerow(flat)
    print(f"[Export] CSV saved -> {csv_path}")


def evaluate_pipeline(dataset_path: str, output_path: str, use_hybrid: bool = True):
    """
    Evaluate tagging pipeline against hand-labeled dataset.
    Computes precision, recall, and F1 scores.
    """
    print(f"[Eval] Loading dataset: {dataset_path}")
    dataset = load_evaluation_dataset(dataset_path)
    
    evaluator = TaggingEvaluator()
    
    # Initialize tagger
    if use_hybrid:
        print("[Eval] Using hybrid semantic tagger")
        tagger = HybridSemanticTagger()
    else:
        print("[Eval] Using legacy rule-based tagger")
        tagger = None
    
    # Process each FOA in dataset
    for foa in dataset:
        foa_id = foa.get("foa_id", "UNKNOWN")
        title = foa.get("title", "")
        description = foa.get("description", "")
        gold_tags = foa.get("gold_tags", {})
        
        # Combine text for tagging
        combined_text = f"{title} {description}"
        
        # Get predictions
        if use_hybrid:
            predicted_tags = tagger.apply_tags(combined_text)
        else:
            predicted_tags = apply_tags_legacy(combined_text)
        
        # Evaluate each category
        for category in gold_tags.keys():
            gold = gold_tags.get(category, [])
            predicted = predicted_tags.get(category, [])
            
            evaluator.add_prediction(foa_id, category, predicted, gold)
    
    # Print and save results
    print("\n" + "="*60)
    evaluator.print_summary()
    evaluator.export_results(output_path)
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="FOA Funding Intelligence Pipeline (Extended)")
    parser.add_argument("--url",     required=False, help="FOA URL/ID (NSF, Grants.gov, or NIH)")
    parser.add_argument("--out_dir", default="./out", help="Output directory")
    parser.add_argument("--hybrid",  action="store_true", default=True, help="Use hybrid tagging (default)")
    parser.add_argument("--legacy",  action="store_true", help="Use legacy rule-based tagging")
    parser.add_argument("--eval",    help="Evaluate against hand-labeled dataset (JSON file)")
    parser.add_argument("--eval_out", default="./eval_results.json", help="Evaluation results output")
    
    args = parser.parse_args()

    # If evaluation mode, skip FOA ingestion
    if args.eval:
        print(f"\n{'='*60}")
        print("  EVALUATION MODE")
        print(f"  Dataset: {args.eval}")
        print(f"{'='*60}\n")
        
        evaluate_pipeline(args.eval, args.eval_out, use_hybrid=(not args.legacy))
        return

    # Normal mode: ingest and tag single FOA
    if not args.url:
        parser.print_help()
        sys.exit(1)

    print(f"\n{'='*60}")
    print("  FOA Ingestion Pipeline (Extended with NIH + Hybrid Tagging)")
    print(f"  URL/ID: {args.url}")
    print(f"  Output: {args.out_dir}")
    print(f"  Tagging: {'Hybrid (embeddings + keywords)' if not args.legacy else 'Legacy (rule-based)'}")
    print(f"{'='*60}\n")

    # Step 1: Ingest
    print("[Step 1/3] Fetching FOA data...")
    foa = ingest_foa(args.url)

    # Step 2: Apply tags
    print("[Step 2/3] Applying semantic tags...")
    combined_text = f"{foa.get('title','')} {foa.get('description','')} {foa.get('eligibility','')}"
    
    if args.legacy:
        # Legacy rule-based tagging
        foa["tags"] = apply_tags_legacy(combined_text)
    else:
        # Hybrid tagging with embeddings
        tagger = HybridSemanticTagger()
        foa["tags"] = tagger.apply_tags(combined_text)

    # Step 3: Export
    print("[Step 3/3] Exporting results...")
    export(foa, args.out_dir)

    print("\n[OK] Done! Files written to:", args.out_dir)
    print("\n-- Extracted Fields --")
    for k, v in foa.items():
        if k == "tags":
            print(f"  tags:")
            for cat, vals in v.items():
                if vals:
                    print(f"    {cat}: {vals}")
        elif k == "description":
            print(f"  description: {str(v)[:120]}...")
        else:
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
