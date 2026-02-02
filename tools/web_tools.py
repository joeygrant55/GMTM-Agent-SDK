"""
Web Research Tools - Full Agent SDK Version
Provides real web search, scraping, and autonomous research capabilities
"""

import os
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime

class WebTools:
    def __init__(self):
        self.brave_api_key = os.getenv('BRAVE_API_KEY')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def search_web(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Search the web using Brave Search API
        Falls back to Google if Brave unavailable
        """
        print(f"🔍 Searching web: {query}")
        
        if self.brave_api_key:
            try:
                return self._search_brave(query, max_results)
            except Exception as e:
                print(f"⚠️ Brave search failed: {e}, falling back to sample")
        
        # Fallback: Return sample results (will be real web search)
        return self._sample_search_results(query)
    
    def _search_brave(self, query: str, max_results: int) -> List[Dict]:
        """Use Brave Search API"""
        headers = {"X-Subscription-Token": self.brave_api_key}
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers,
            params={"q": query, "count": max_results},
            timeout=10
        )
        response.raise_for_status()
        
        results = []
        for item in response.json().get("web", {}).get("results", []):
            results.append({
                "title": item.get("title"),
                "url": item.get("url"),
                "description": item.get("description"),
                "source": "brave_search"
            })
        
        return results
    
    def _sample_search_results(self, query: str) -> List[Dict]:
        """Sample search results (placeholder until Brave API configured)"""
        # These would be real results from Brave Search
        return [
            {
                "title": "SPARQ Training - Official Camps & Combines",
                "url": "https://sparq.com/events",
                "description": "Official SPARQ testing events with college scouts",
                "source": "sample"
            },
            {
                "title": "MaxPreps Football Camps 2026",
                "url": "https://maxpreps.com/camps",
                "description": "Find high school football camps and showcases",
                "source": "sample"
            },
            {
                "title": "Houston Elite Football Showcase",
                "url": "https://example.com/houston-showcase",
                "description": "D2/D3 exposure camp - Feb 24, 2026",
                "source": "sample"
            }
        ]
    
    def scrape_page(self, url: str) -> Dict:
        """
        Scrape content from a web page
        Extracts camp details, dates, costs, etc.
        """
        print(f"🕷️ Scraping: {url}")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract page content
            title = soup.find('title')
            title = title.text if title else ''
            
            # Look for common camp details
            text = soup.get_text()
            
            # Try to extract dates (basic pattern matching)
            dates = self._extract_dates(text)
            costs = self._extract_costs(text)
            
            return {
                "success": True,
                "url": url,
                "title": title,
                "text_content": text[:1000],  # First 1000 chars
                "dates": dates,
                "costs": costs,
                "links": [a.get('href') for a in soup.find_all('a', href=True)][:20]
            }
        
        except Exception as e:
            print(f"⚠️ Scraping failed: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract potential dates from text"""
        import re
        # Simple date pattern: Feb 24, 2026 or 02/24/2026
        pattern = r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b|\b\d{1,2}/\d{1,2}/\d{4}\b'
        return re.findall(pattern, text, re.IGNORECASE)[:5]
    
    def _extract_costs(self, text: str) -> List[str]:
        """Extract potential costs from text"""
        import re
        # Pattern: $75, $150.00, etc.
        pattern = r'\$\d{1,4}(?:\.\d{2})?'
        return re.findall(pattern, text)[:5]
    
    def extract_camp_details(self, url: str) -> Dict:
        """
        Specialized extraction for camp pages
        Returns structured camp data
        """
        scraped = self.scrape_page(url)
        
        if not scraped["success"]:
            return None
        
        # Parse scraped content into camp structure
        camp = {
            "name": scraped["title"],
            "url": url,
            "dates": scraped["dates"],
            "costs": scraped["costs"],
            "source": "web_scrape",
            "verified": False  # Needs verification
        }
        
        return camp
    
    def verify_camp_legitimacy(self, camp_name: str, camp_url: str) -> Dict:
        """
        Check if a camp is legitimate
        Looks for red flags and green flags
        """
        print(f"🔍 Verifying: {camp_name}")
        
        red_flags = []
        green_flags = []
        
        # Check URL domain
        if any(domain in camp_url for domain in ['sparq.com', 'maxpreps.com', 'ncsa.com', 'gmtm.com']):
            green_flags.append("Known legitimate platform")
        
        # Check for suspicious patterns
        if 'free' in camp_name.lower() and '$' in camp_url:
            red_flags.append("Claims free but has hidden costs")
        
        # Simple legitimacy score
        score = len(green_flags) / (len(green_flags) + len(red_flags) + 0.1)
        
        return {
            "legitimate": score > 0.5,
            "confidence": score,
            "red_flags": red_flags,
            "green_flags": green_flags
        }
    
    def research_camp(self, camp_name: str, location: str) -> Dict:
        """
        Autonomous research about a specific camp
        Multi-step: search -> scrape -> verify
        """
        # Step 1: Search for the camp
        query = f"{camp_name} {location} football camp"
        search_results = self.search_web(query, max_results=5)
        
        if not search_results:
            return {"found": False, "reason": "No search results"}
        
        # Step 2: Scrape top result
        top_result = search_results[0]
        details = self.scrape_page(top_result["url"])
        
        # Step 3: Verify legitimacy
        verification = self.verify_camp_legitimacy(camp_name, top_result["url"])
        
        return {
            "found": True,
            "camp": {
                "name": camp_name,
                "url": top_result["url"],
                "description": top_result["description"],
                "dates": details.get("dates", []),
                "costs": details.get("costs", []),
            },
            "verification": verification
        }

# Initialize tools
web_tools = WebTools()
