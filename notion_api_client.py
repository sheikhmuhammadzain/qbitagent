"""
Notion API Client - Direct Notion API Integration
Provides tools for interacting with Notion workspaces using stored OAuth tokens.
"""
import httpx
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NotionAPIClient:
    """Client for Direct Notion API Integration
    
    This client connects directly to Notion's REST API using OAuth tokens
    and provides common tools that AI agents need for Notion integration.
    """
    
    def __init__(self, access_token: str):
        """Initialize Notion API Client
        
        Args:
            access_token: OAuth access token from Notion (starts with ntn_ or secret_)
        """
        self.access_token = access_token
        self.notion_api_base = "https://api.notion.com/v1"
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True
        )
        self.connected = False
        
        # Define available tools
        self.tools = [
            {
                "name": "list_databases",
                "description": "List all databases in the Notion workspace",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "search_notion",
                "description": "Search for pages and databases in Notion",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query string"
                        },
                        "filter": {
                            "type": "object",
                            "description": "Optional filter for object type (page or database)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_page",
                "description": "Get a specific page by ID",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Notion page ID"
                        }
                    },
                    "required": ["page_id"]
                }
            },
            {
                "name": "query_database",
                "description": "Query a database with optional filters and sorting",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "Database ID to query"
                        },
                        "filter": {
                            "type": "object",
                            "description": "Optional filter criteria"
                        },
                        "sorts": {
                            "type": "array",
                            "description": "Optional sort criteria"
                        }
                    },
                    "required": ["database_id"]
                }
            },
            {
                "name": "get_database",
                "description": "Get database structure and properties",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "Database ID to retrieve"
                        }
                    },
                    "required": ["database_id"]
                }
            },
            {
                "name": "create_page",
                "description": "Create a new page in a database with properties and content",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "Parent database ID"
                        },
                        "properties": {
                            "type": "object",
                            "description": "Page properties (title, rich_text, select, etc.)"
                        },
                        "children": {
                            "type": "array",
                            "description": "Optional content blocks to add to the page"
                        }
                    },
                    "required": ["database_id", "properties"]
                }
            },
            {
                "name": "update_page",
                "description": "Update page properties",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Page ID to update"
                        },
                        "properties": {
                            "type": "object",
                            "description": "Properties to update"
                        }
                    },
                    "required": ["page_id", "properties"]
                }
            },
            {
                "name": "append_block",
                "description": "Append content blocks to a page",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "block_id": {
                            "type": "string",
                            "description": "Page or block ID to append to"
                        },
                        "children": {
                            "type": "array",
                            "description": "Content blocks to append (paragraphs, headings, lists, etc.)"
                        }
                    },
                    "required": ["block_id", "children"]
                }
            }
        ]
    
    async def connect(self) -> bool:
        """Test connection and validate token
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            response = await self.client.get(
                f"{self.notion_api_base}/users/me",
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                self.connected = True
                user_info = response.json()
                logger.info(f"✅ Connected to Notion API. User: {user_info.get('name', 'Unknown')}")
                return True
            else:
                logger.error(f"❌ Failed to connect to Notion API: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Connection error: {e}", exc_info=True)
            return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Notion tool
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments as dictionary
            
        Returns:
            Dict containing tool execution results or error information
        """
        if not self.connected:
            return {
                "error": "Not connected to Notion API",
                "details": "Please call connect() first"
            }
        
        try:
            logger.info(f"🔧 Calling Notion tool: {tool_name}")
            logger.debug(f"   Arguments: {json.dumps(arguments, indent=2)}")
            
            if tool_name == "list_databases":
                return await self._list_databases()
            elif tool_name == "search_notion":
                return await self._search_notion(arguments.get("query"), arguments.get("filter"))
            elif tool_name == "get_page":
                return await self._get_page(arguments.get("page_id"))
            elif tool_name == "query_database":
                return await self._query_database(
                    arguments.get("database_id"),
                    arguments.get("filter"),
                    arguments.get("sorts")
                )
            elif tool_name == "get_database":
                return await self._get_database(arguments.get("database_id"))
            elif tool_name == "create_page":
                return await self._create_page(
                    arguments.get("database_id"),
                    arguments.get("properties", {}),
                    arguments.get("children")
                )
            elif tool_name == "update_page":
                return await self._update_page(
                    arguments.get("page_id"),
                    arguments.get("properties", {})
                )
            elif tool_name == "append_block":
                return await self._append_block(
                    arguments.get("block_id"),
                    arguments.get("children", [])
                )
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            logger.error(f"❌ Tool call error: {e}", exc_info=True)
            return {
                "error": f"Tool execution failed: {str(e)}",
                "tool_name": tool_name
            }
    
    async def _list_databases(self) -> Dict[str, Any]:
        """List all databases"""
        response = await self.client.post(
            f"{self.notion_api_base}/search",
            headers=self._get_headers(),
            json={
                "filter": {"object": "database"}
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            databases = []
            for db in data.get("results", []):
                databases.append({
                    "id": db.get("id"),
                    "title": self._extract_title(db),
                    "url": db.get("url"),
                    "created_time": db.get("created_time"),
                    "last_edited_time": db.get("last_edited_time")
                })
            return {"databases": databases}
        else:
            return {"error": f"Failed to list databases: {response.text}"}
    
    async def _search_notion(self, query: str, filter_obj: Optional[Dict] = None) -> Dict[str, Any]:
        """Search Notion"""
        search_body = {"query": query}
        if filter_obj:
            search_body["filter"] = filter_obj
            
        response = await self.client.post(
            f"{self.notion_api_base}/search",
            headers=self._get_headers(),
            json=search_body
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("results", []):
                results.append({
                    "id": item.get("id"),
                    "object": item.get("object"),
                    "title": self._extract_title(item),
                    "url": item.get("url"),
                    "created_time": item.get("created_time")
                })
            return {"results": results, "has_more": data.get("has_more", False)}
        else:
            return {"error": f"Search failed: {response.text}"}
    
    async def _get_page(self, page_id: str) -> Dict[str, Any]:
        """Get page details"""
        response = await self.client.get(
            f"{self.notion_api_base}/pages/{page_id}",
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to get page: {response.text}"}
    
    async def _query_database(self, database_id: str, filter_obj: Optional[Dict] = None, sorts: Optional[List] = None) -> Dict[str, Any]:
        """Query database"""
        query_body = {}
        if filter_obj:
            query_body["filter"] = filter_obj
        if sorts:
            query_body["sorts"] = sorts
            
        response = await self.client.post(
            f"{self.notion_api_base}/databases/{database_id}/query",
            headers=self._get_headers(),
            json=query_body
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Database query failed: {response.text}"}
    
    async def _get_database(self, database_id: str) -> Dict[str, Any]:
        """Get database structure"""
        response = await self.client.get(
            f"{self.notion_api_base}/databases/{database_id}",
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to get database: {response.text}"}
    
    async def _create_page(self, database_id: str, properties: Dict, children: Optional[List] = None) -> Dict[str, Any]:
        """Create a new page in a database"""
        payload = {
            "parent": {"database_id": database_id},
            "properties": properties
        }
        
        if children:
            payload["children"] = children
        
        response = await self.client.post(
            f"{self.notion_api_base}/pages",
            headers=self._get_headers(),
            json=payload
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to create page: {response.text}"}
    
    async def _update_page(self, page_id: str, properties: Dict) -> Dict[str, Any]:
        """Update page properties"""
        response = await self.client.patch(
            f"{self.notion_api_base}/pages/{page_id}",
            headers=self._get_headers(),
            json={"properties": properties}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to update page: {response.text}"}
    
    async def _append_block(self, block_id: str, children: List) -> Dict[str, Any]:
        """Append blocks to a page"""
        response = await self.client.patch(
            f"{self.notion_api_base}/blocks/{block_id}/children",
            headers=self._get_headers(),
            json={"children": children}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to append blocks: {response.text}"}
    
    def _extract_title(self, notion_object: Dict) -> str:
        """Extract title from Notion object"""
        if "title" in notion_object and notion_object["title"]:
            # For pages
            title_parts = []
            for part in notion_object["title"]:
                if "plain_text" in part:
                    title_parts.append(part["plain_text"])
            return "".join(title_parts) if title_parts else "Untitled"
        elif "properties" in notion_object:
            # For databases, look for title property
            for prop_name, prop_data in notion_object["properties"].items():
                if prop_data.get("type") == "title":
                    return prop_name
        return "Untitled"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Notion API"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    async def close(self):
        """Close the HTTP client"""
        try:
            await self.client.aclose()
            self.connected = False
            logger.info("🔌 Notion API client closed")
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
        status = "connected" if self.connected else "disconnected"
        tools_count = len(self.tools)
        return f"<NotionAPIClient status={status} tools={tools_count}>"