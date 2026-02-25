

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# rule - based ontology for tagging
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
    
    resp = requests.get(api_url, timeout=15)
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

def fetch_nsf(url: str) -> dict:

    print(f"[NSF] Scraping page: {url}")
    headers = {"User-Agent": "Mozilla/5.0 (research pipeline)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
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

    nsf_id_match = re.search(r'/(\d{3,})', url)
    foa_id = nsf_id_match.group(1) if nsf_id_match else "NSF-UNKNOWN"

    description = ""
    for selector in ["div.field--name-body", "div#synopsis", "div.view-mode-full", "main"]:
        el = soup.select_one(selector)
        if el:
            description = el.get_text(separator=" ", strip=True)[:3000]
            break

    open_date  = find_by_label("open date") or find_by_label("posted") or ""
    close_date = find_by_label("deadline") or find_by_label("due date") or find_by_label("close") or ""


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
    if "grants.gov" in url.lower():
        return fetch_grants_gov(url)
    elif "nsf.gov" in url.lower():
        return fetch_nsf(url)
    else:
        raise ValueError(
            f"Unsupported source. URL must be from grants.gov or nsf.gov.\nGot: {url}"
        )


def export(record: dict, out_dir: str):

    os.makedirs(out_dir, exist_ok=True)

    # JSON 
    json_path = os.path.join(out_dir, "foa.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    print(f"[Export] JSON saved → {json_path}")

    # CSV 
    csv_path = os.path.join(out_dir, "foa.csv")
    flat = {k: v for k, v in record.items() if k != "tags"}

    for category, values in record.get("tags", {}).items():
        flat[f"tag_{category}"] = "; ".join(values)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=flat.keys())
        writer.writeheader()
        writer.writerow(flat)
    print(f"[Export] CSV saved → {csv_path}")


def main():
    parser = argparse.ArgumentParser(description="FOA Funding Intelligence Pipeline")
    parser.add_argument("--url",     required=True, help="URL of the FOA page (grants.gov or nsf.gov)")
    parser.add_argument("--out_dir", default="./out", help="Output directory for foa.json and foa.csv")
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"  FOA Ingestion Pipeline")
    print(f"  URL: {args.url}")
    print(f"  Output: {args.out_dir}")
    print(f"{'='*50}\n")

    # Ingest
    print("[Step 1/3] Fetching FOA data...")
    foa = ingest_foa(args.url)

    # Tag
    print("[Step 2/3] Applying semantic tags...")
    combined_text = f"{foa.get('title','')} {foa.get('description','')} {foa.get('eligibility','')}"
    foa["tags"] = apply_tags(combined_text)

    # Export
    print("[Step 3/3] Exporting results...")
    export(foa, args.out_dir)

    print("\n✅ Done! Files written to:", args.out_dir)
    print("\n── Extracted Fields ──")
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
