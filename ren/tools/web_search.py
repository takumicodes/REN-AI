"""
REN Web Search Tool
Fetches live, real-time web results for current events, prices, weather, news, and facts.
Ensures REN never hallucinates outdated model knowledge when current information is requested.
"""

import re
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Dict, Any, List, Optional

from ren.tools.base import BaseTool, ToolResult
from ren.security.permissions import PermissionCategory
from ren.monitoring.logger import tools_logger, error_logger


class WebSearchTool(BaseTool):
    """Searches the live web for current real-time data and facts."""

    name = "web_search"
    description = (
        "Search the live web for current real-time information such as today's gold price, "
        "current weather, latest news, market prices, currency exchange rates, sports scores, or recent facts."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Specific search terms to look up current live web data."
            }
        },
        "required": ["query"]
    }
    required_permissions = [PermissionCategory.NETWORK_REQUEST]

    def run(self, **kwargs) -> ToolResult:
        start_t = time.time()
        query = str(kwargs.get("query", "")).strip()
        if not query:
            return ToolResult(
                success=False,
                output="",
                error="Search query cannot be empty.",
                duration=time.time() - start_t
            )

        tools_logger.info(f"Executing live web search for: '{query}'")
        current_date_str = datetime.utcnow().strftime("%Y-%m-%d")

        # 1. Try DuckDuckGo Instant Answers API
        instant_answer = self._try_ddg_instant_answer(query)
        if instant_answer:
            output = (
                f"[Live Web Search - Date: {current_date_str}]\n"
                f"Query: '{query}'\n"
                f"Answer: {instant_answer}"
            )
            return ToolResult(success=True, output=output, duration=time.time() - start_t)

        # 2. Try DuckDuckGo HTML / Lite Search
        web_snippets = self._try_ddg_html_search(query)
        if web_snippets:
            formatted_snippets = "\n".join([f"- {s}" for s in web_snippets[:5]])
            output = (
                f"[Live Web Search Results - Current Date: {current_date_str}]\n"
                f"Query: '{query}'\n"
                f"Key Live Web Findings:\n{formatted_snippets}"
            )
            return ToolResult(success=True, output=output, duration=time.time() - start_t)

        # 3. Try Wikipedia OpenSearch Fallback
        wiki_snippets = self._try_wikipedia_search(query)
        if wiki_snippets:
            formatted_wiki = "\n".join([f"- {s}" for s in wiki_snippets[:4]])
            output = (
                f"[Wikipedia Live Search - Date: {current_date_str}]\n"
                f"Query: '{query}'\n"
                f"Findings:\n{formatted_wiki}"
            )
            return ToolResult(success=True, output=output, duration=time.time() - start_t)

        # Explicit unverified response to prevent hallucination
        return ToolResult(
            success=False,
            output="Current live information could not be verified from the web.",
            error="No verified search results returned.",
            duration=time.time() - start_t
        )

    def _try_ddg_instant_answer(self, query: str) -> Optional[str]:
        """Queries DuckDuckGo Instant Answer API."""
        try:
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) REN-AI/2.5"})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                # Check Abstract or Answer
                answer = data.get("Answer") or data.get("AbstractText")
                if answer and len(answer.strip()) > 10:
                    return answer.strip()

                # Check RelatedTopics
                topics = data.get("RelatedTopics", [])
                snippets = []
                for t in topics[:3]:
                    if isinstance(t, dict) and "Text" in t:
                        snippets.append(t["Text"])
                if snippets:
                    return "\n".join(snippets)
        except Exception as e:
            tools_logger.debug(f"DDG Instant Answer error: {e}")
        return None

    def _try_ddg_html_search(self, query: str) -> List[str]:
        """Queries DuckDuckGo HTML for real-time snippets."""
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                html = response.read().decode("utf-8", errors="ignore")
                
                # Extract snippets
                snippet_pattern = re.compile(r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>', re.DOTALL)
                matches = snippet_pattern.findall(html)
                
                clean_snippets = []
                for m in matches:
                    text = re.sub(r'<[^>]+>', '', m).strip()
                    text = re.sub(r'\s+', ' ', text)
                    if text and len(text) > 20:
                        clean_snippets.append(text)

                return clean_snippets
        except Exception as e:
            tools_logger.debug(f"DDG HTML search error: {e}")
        return []

    def _try_wikipedia_search(self, query: str) -> List[str]:
        """Queries Wikipedia OpenSearch API as reliable fallback."""
        try:
            url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(query)}&limit=3&namespace=0&format=json"
            req = urllib.request.Request(url, headers={"User-Agent": "REN-AI-Assistant/2.5"})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                if len(data) >= 3 and isinstance(data[2], list):
                    return [d for d in data[2] if d and len(d.strip()) > 10]
        except Exception as e:
            tools_logger.debug(f"Wikipedia search error: {e}")
        return []
