#!/usr/bin/env python3
"""
Quick tester to find working FOA URLs and validate scrapers
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def test_url(url, name=""):
    """Test if a URL returns content and what status"""
    print(f"\n{'='*60}")
    print(f"Testing: {name or url}")
    print(f"URL: {url}")
    print('='*60)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        print(f"Status: {resp.status_code}")
        print(f"Final URL: {resp.url}")
        print(f"Content-Type: {resp.headers.get('content-type', 'unknown')}")
        print(f"Content length: {len(resp.text)} chars")
        
        # Parse content
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.find("title")
        h1 = soup.find("h1")
        
        print(f"Page title: {title.get_text(strip=True) if title else 'N/A'}")
        print(f"H1: {h1.get_text(strip=True) if h1 else 'N/A'}")
        
        # Check if it's a real FOA page
        if "session" in resp.text.lower() or "login" in resp.text.lower():
            print("⚠️  WARNING: Page contains session/login content")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

# Test various NSF URLs
print("\n\n" + "="*60)
print("TESTING NSF URLS")
print("="*60)

nsf_urls = [
    ("https://www.nsf.gov/cgi-bin/getpub?nsf24520", "NSF24-520 (cgi-bin)"),
    ("https://www.nsf.gov/pubs/2024/nsf24520/nsf24520.pdf", "NSF24-520 (PDF)"),
    ("https://new.nsf.gov/funding/opportunities/nsf-24-520", "NSF24-520 (new.nsf.gov)"),
    ("https://www.nsf.gov/funding/opportunities/", "NSF Opportunities listing"),
]

for url, name in nsf_urls:
    test_url(url, name)

# Test Grants.gov
print("\n\n" + "="*60)
print("TESTING GRANTS.GOV URLS")
print("="*60)

grants_urls = [
    ("https://www.grants.gov/search-results-detail/350693", "Direct search result"),
    ("https://apply07.grants.gov/grantsws/rest/opportunity/details?oppId=350693", "REST API (direct)"),
]

for url, name in grants_urls:
    test_url(url, name)

print("\n\n" + "="*60)
print("RECOMMENDATIONS:")
print("="*60)
print("""
1. For NSF: Use CGI-BIN URLs or visit https://www.nsf.gov/funding/opportunities/
   and find solicitation numbers there

2. For Grants.gov: The session issue requires either:
   - Using a proper session/cookie approach
   - Or finding alternative APIs
   - Or updating the scraper to handle redirects

3. Try running with sample URLs above to see which ones work
""")
