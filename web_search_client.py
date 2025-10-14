"""
Web Search Client - Serper API Integration
Provides web search capabilities for AI agents using Serper.dev API
"""
import httpx
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Hardcoded Serper API key
SERPER_API_KEY = "6f22740926cf18ceabeceb4d51b8f50694258694"


class WebSearchClient:
    """Client for Web Search using Serper API
    
    This client provides web search capabilities including:
    - Google search results
    - News search
    - Image search
    - Shopping search
    """
    
    def __init__(self):
        """Initialize Web Search Client"""
        self.api_key = SERPER_API_KEY
        self.serper_api_base = "https://google.serper.dev"
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True
        )
        self.connected = True
        
        # Define available tools
        self.tools = [
            {
                "name": "web_search",
                "description": "Search the web using Google. Returns web pages, snippets, and links.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query string"
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of results to return (default: 10, max: 100)",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "news_search",
                "description": "Search for recent news articles",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "News search query"
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of results (default: 10)",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "image_search",
                "description": "Search for images",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Image search query"
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of images (default: 10)",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "shopping_search",
                "description": "Search for shopping/product results",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Product search query"
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of products (default: 10)",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            }
        ]
    
    async def connect(self) -> bool:
        """Test connection by making a simple search
        
        Returns:
            bool: True if connection successful
        """
        try:
            # Test with a simple query
            response = await self.client.post(
                f"{self.serper_api_base}/search",
                headers=self._get_headers(),
                json={"q": "test", "num": 1}
            )
            
            if response.status_code == 200:
                logger.info("✅ Connected to Serper API (Web Search)")
                return True
            else:
                logger.error(f"❌ Failed to connect to Serper API: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Connection error: {e}", exc_info=True)
            return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a web search tool
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments as dictionary
            
        Returns:
            Dict containing search results or error information
        """
        try:
            logger.info(f"🔍 Calling web search tool: {tool_name}")
            logger.debug(f"   Arguments: {json.dumps(arguments, indent=2)}")
            
            if tool_name == "web_search":
                return await self._web_search(
                    arguments.get("query"),
                    arguments.get("num_results", 10)
                )
            elif tool_name == "news_search":
                return await self._news_search(
                    arguments.get("query"),
                    arguments.get("num_results", 10)
                )
            elif tool_name == "image_search":
                return await self._image_search(
                    arguments.get("query"),
                    arguments.get("num_results", 10)
                )
            elif tool_name == "shopping_search":
                return await self._shopping_search(
                    arguments.get("query"),
                    arguments.get("num_results", 10)
                )
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            logger.error(f"❌ Tool call error: {e}", exc_info=True)
            return {
                "error": f"Tool execution failed: {str(e)}",
                "tool_name": tool_name
            }
    
    async def _web_search(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """Perform web search"""
        response = await self.client.post(
            f"{self.serper_api_base}/search",
            headers=self._get_headers(),
            json={
                "q": query,
                "num": min(num_results, 100)
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            results = []
            for item in data.get("organic", []):
                results.append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet"),
                    "position": item.get("position")
                })
            
            return {
                "query": query,
                "results": results,
                "searchInformation": data.get("searchInformation", {}),
                "knowledgeGraph": data.get("knowledgeGraph"),
                "answerBox": data.get("answerBox")
            }
        else:
            return {"error": f"Web search failed: {response.status_code} - {response.text}"}
    
    async def _news_search(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """Search news"""
        response = await self.client.post(
            f"{self.serper_api_base}/news",
            headers=self._get_headers(),
            json={
                "q": query,
                "num": min(num_results, 100)
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            news = []
            for item in data.get("news", []):
                news.append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet"),
                    "date": item.get("date"),
                    "source": item.get("source"),
                    "imageUrl": item.get("imageUrl")
                })
            
            return {
                "query": query,
                "news": news,
                "searchInformation": data.get("searchInformation", {})
            }
        else:
            return {"error": f"News search failed: {response.status_code} - {response.text}"}
    
    async def _image_search(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """Search images"""
        response = await self.client.post(
            f"{self.serper_api_base}/images",
            headers=self._get_headers(),
            json={
                "q": query,
                "num": min(num_results, 100)
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            images = []
            for item in data.get("images", []):
                images.append({
                    "title": item.get("title"),
                    "imageUrl": item.get("imageUrl"),
                    "imageWidth": item.get("imageWidth"),
                    "imageHeight": item.get("imageHeight"),
                    "thumbnailUrl": item.get("thumbnailUrl"),
                    "source": item.get("source"),
                    "link": item.get("link")
                })
            
            return {
                "query": query,
                "images": images
            }
        else:
            return {"error": f"Image search failed: {response.status_code} - {response.text}"}
    
    async def _shopping_search(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """Search shopping/products"""
        response = await self.client.post(
            f"{self.serper_api_base}/shopping",
            headers=self._get_headers(),
            json={
                "q": query,
                "num": min(num_results, 100)
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            products = []
            for item in data.get("shopping", []):
                products.append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "price": item.get("price"),
                    "source": item.get("source"),
                    "rating": item.get("rating"),
                    "ratingCount": item.get("ratingCount"),
                    "imageUrl": item.get("imageUrl")
                })
            
            return {
                "query": query,
                "products": products
            }
        else:
            return {"error": f"Shopping search failed: {response.status_code} - {response.text}"}
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Serper API"""
        return {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def close(self):
        """Close the HTTP client"""
        try:
            await self.client.aclose()
            logger.info("🔌 Web search client closed")
        except Exception as e:
            logger.error(f"Error closing client: {e}")
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return [tool["name"] for tool in self.tools]
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tool"""
        for tool in self.tools:
            if tool["name"] == tool_name:
                return tool
        return None
    
    def __repr__(self) -> str:
        tools_count = len(self.tools)
        return f"<WebSearchClient tools={tools_count}>"
