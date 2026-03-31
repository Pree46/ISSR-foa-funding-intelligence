"""
NIH Project Reporting System (RePORTER) API integration
Fetches funded research projects, converts to FOA-like format
"""
import requests
from typing import Dict, Optional

from foa_pipeline.utils.logger import get_logger

log = get_logger(__name__)


def fetch_nih_project(project_id: str) -> Dict:
    """
    Fetch NIH project details from RePORTER API.
    
    Args:
        project_id: NIH Project ID (e.g., "R01CA123456")
        
    Returns:
        Normalized FOA-like record
    """
    log.info("Fetching NIH project: %s", project_id)
    
    # NIH RePORTER API endpoint (no auth required for public data)
    api_url = "https://api.federalreporter.nih.gov/v2/projects/search"
    
    payload = {
        "criteria": {
            "project_numbers": [project_id]
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "FOA-Pipeline/1.0"
    }
    
    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        if not data.get("projects") or len(data["projects"]) == 0:
            raise ValueError(f"No project found with ID: {project_id}")
        
        project = data["projects"][0]
        return _normalize_nih_project(project, project_id)
        
    except requests.exceptions.RequestException as e:
        log.error("Failed to fetch NIH project: %s", e)
        raise


def fetch_nih_by_keyword(keyword: str, limit: int = 1) -> Dict:
    """
    Search NIH projects by keyword.
    
    Args:
        keyword: Search keyword (e.g., "machine learning")
        limit: Max results to fetch
        
    Returns:
        First matching project as FOA-like record
    """
    log.info("Searching NIH for keyword: %s", keyword)
    
    api_url = "https://api.federalreporter.nih.gov/v2/projects/search"
    
    payload = {
        "criteria": {
            "text_search": keyword
        },
        "limit": limit
    }
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "FOA-Pipeline/1.0"
    }
    
    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        if not data.get("projects") or len(data["projects"]) == 0:
            raise ValueError(f"No projects found for keyword: {keyword}")
        
        project = data["projects"][0]
        return _normalize_nih_project(project, None)
        
    except requests.exceptions.RequestException as e:
        log.error("NIH Search failed: %s", e)
        raise


def _normalize_nih_project(project: Dict, project_id: Optional[str] = None) -> Dict:
    """
    Convert NIH RepORTER project to FOA-like schema
    """
    # Extract key fields
    project_number = project_id or project.get("projectNumber", "NIH-UNKNOWN")
    title = project.get("title", "")
    abstract = project.get("abstractText", "")
    org = project.get("organization", {})
    org_name = org.get("name", "National Institutes of Health (NIH)")
    
    # Parse dates
    start_date = project.get("projectStartDate")
    end_date = project.get("projectEndDate")
    
    # Award info
    award_amount = project.get("totalCost")
    
    return {
        "foa_id": project_number,
        "title": title,
        "agency": org_name,
        "open_date": start_date or "",
        "close_date": end_date or "",
        "eligibility": "",  # NIH projects are already awarded
        "description": abstract[:3000] if abstract else "",
        "award_range": f"${award_amount:,.0f}" if award_amount else "",
        "source_url": f"https://reporter.nih.gov/project-details/{project_number}",
        "source": "NIH",
    }
