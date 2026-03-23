"""
NIH Project Reporting System (RePORTER) API integration
Fetches funded research projects, converts to FOA-like format
"""
import requests
import json
from datetime import datetime
from typing import Dict, Optional


def fetch_nih_project(project_id: str) -> Dict:
    """
    Fetch NIH project details from RePORTER API.
    
    Args:
        project_id: NIH Project ID (e.g., "R01CA123456")
        
    Returns:
        Normalized FOA-like record
    """
    print(f"[NIH] Fetching project: {project_id}")
    
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
        print(f"[NIH ERROR] Failed to fetch project: {e}")
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
    print(f"[NIH] Searching for keyword: {keyword}")
    
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
        print(f"[NIH ERROR] Search failed: {e}")
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
    fy = project.get("fiscalYear")
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


def search_nih_funding_opportunities(topic: str) -> str:
    """
    Helper to search NIH funding opportunities (Open Funding Notices).
    Note: This is informational - NIH uses a different structure than traditional FOAs.
    
    Args:
        topic: Search topic (e.g., "machine learning", "clinical trials")
        
    Returns:
        Formatted string with opportunity info
    """
    print(f"[NIH] Searching funding notices for: {topic}")
    
    try:
        # NIH Funding Opportunities search
        url = "https://grants.nih.gov/grants/guide/search-results.htm"
        params = {
            "key": topic,
            "s1": "PA",  # Program Announcements
            "s2": "RFP",  # Requests for Applications
        }
        
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        
        # This would need HTML parsing; for now, return search URL
        return f"Search NIH opportunities at: {url}?key={topic}"
        
    except Exception as e:
        return f"Could not search NIH opportunities: {e}"
