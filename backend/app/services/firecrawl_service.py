"""
Firecrawl Service - Simple HTTP-based web search
Uses Firecrawl API directly instead of MCP protocol
"""
import httpx
from typing import Optional, Dict, Any
from app.core.config import settings


class FirecrawlService:
    """Simple Firecrawl API integration for web search"""
    
    def __init__(self):
        self.api_key = settings.FIRECRAWL_API_KEY
        self.base_url = "https://api.firecrawl.dev/v1"
        self.client = httpx.AsyncClient(timeout=60.0)  # Increased timeout for scraping
    
    async def search(self, query: str, limit: int = 3) -> Optional[str]:
        """
        Search the web using Firecrawl and scrape top results
        
        Args:
            query: Search query
            limit: Number of results to scrape (default 3 to avoid timeout)
            
        Returns:
            Formatted search results with actual content, or None if failed
        """
        if not self.api_key:
            print("[Firecrawl] API key not configured")
            return None
        
        try:
            print(f"[Firecrawl] Searching for: {query}")
            
            # First, search to get URLs
            response = await self.client.post(
                f"{self.base_url}/search",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "query": query,
                    "limit": limit,
                    "scrapeOptions": {
                        "formats": ["markdown"]
                    }
                }
            )
            
            if response.status_code != 200:
                print(f"[Firecrawl] Search failed: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            results = data.get("data", [])
            
            if not results:
                print("[Firecrawl] No results found")
                return None
            
            # Format results with content from search
            formatted_results = []
            for i, result in enumerate(results[:limit], 1):
                title = result.get("title", "No title")
                url = result.get("url", "")
                content = result.get("markdown", result.get("content", ""))
                
                # Truncate content to avoid overwhelming the LLM (keep first 800 chars)
                if len(content) > 800:
                    content = content[:800] + "..."
                
                # Only include results with actual content
                if content and len(content) > 50:
                    formatted_results.append(
                        f"**[{i}] {title}**\n"
                        f"🔗 [{url}]({url})\n\n"
                        f"{content}\n"
                    )
            
            if not formatted_results:
                print("[Firecrawl] No content extracted from results")
                return None
            
            result_text = "\n---\n".join(formatted_results)
            print(f"[Firecrawl] Scraped {len(formatted_results)} results with content")
            
            return result_text
            
        except Exception as e:
            print(f"[Firecrawl] Error during search: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def scrape(self, url: str) -> Optional[str]:
        """
        Scrape a specific URL using Firecrawl
        
        Args:
            url: URL to scrape
            
        Returns:
            Scraped content as markdown, or None if failed
        """
        if not self.api_key:
            print("[Firecrawl] API key not configured")
            return None
        
        try:
            print(f"[Firecrawl] Scraping: {url}")
            
            response = await self.client.post(
                f"{self.base_url}/scrape",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "url": url,
                    "formats": ["markdown"]
                }
            )
            
            if response.status_code != 200:
                print(f"[Firecrawl] Scrape failed: {response.status_code} - {response.text}")
                return None
            
            data = response.json()
            content = data.get("data", {}).get("markdown", "")
            
            if not content:
                print("[Firecrawl] No content extracted")
                return None
            
            print(f"[Firecrawl] Scraped {len(content)} characters")
            return content
            
        except Exception as e:
            print(f"[Firecrawl] Error during scrape: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Global Firecrawl service instance
firecrawl_service = FirecrawlService()
