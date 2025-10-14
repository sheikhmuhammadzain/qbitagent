"""
Notion MCP Client - Remote HTTP Connection
Connects to Notion's hosted MCP server with OAuth authentication

This client implements the Model Context Protocol (MCP) for remote server connections,
specifically designed for Notion's API integration.
"""
import httpx
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NotionMCPClient:
    """Client for Notion Remote MCP Server
    
    This client connects to Notion's hosted MCP server at https://mcp.notion.com/mcp
    and provides tool discovery and execution capabilities with OAuth authentication.
    
    Features:
    - OAuth token-based authentication
    - Automatic tool discovery
    - Tool execution with proper error handling
    - Async operations for better performance
    """
    
    def __init__(self, access_token: str, mcp_url: str = "https://mcp.notion.com/mcp"):
        """Initialize Notion MCP Client
        
        Args:
            access_token: OAuth access token from Notion
            mcp_url: MCP server URL (default: https://mcp.notion.com/mcp)
        """
        self.access_token = access_token
        self.mcp_url = mcp_url
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True
        )
        self.tools: List[Dict[str, Any]] = []
        self.connected = False
        self.workspace_info: Optional[Dict[str, Any]] = None
    
    async def connect(self) -> bool:
        """Initialize connection and discover available tools
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Tool discovery via MCP protocol
            response = await self.client.post(
                f"{self.mcp_url}/tools/list",
                headers=self._get_headers(),
                json={}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.tools = data.get("tools", [])
                self.connected = True
                logger.info(f"✅ Connected to Notion MCP. Found {len(self.tools)} tools.")
                
                # Log available tools for debugging
                for tool in self.tools:
                    logger.debug(f"  - {tool.get('name')}: {tool.get('description', 'No description')}")
                
                return True
            else:
                logger.error(f"❌ Failed to connect to Notion MCP: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except httpx.TimeoutException:
            logger.error("⏱️ Timeout connecting to Notion MCP")
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
                "error": "Not connected to Notion MCP",
                "details": "Please call connect() first"
            }
        
        try:
            logger.info(f"🔧 Calling Notion tool: {tool_name}")
            logger.debug(f"   Arguments: {json.dumps(arguments, indent=2)}")
            
            response = await self.client.post(
                f"{self.mcp_url}/tools/call",
                headers=self._get_headers(),
                json={
                    "name": tool_name,
                    "arguments": arguments
                },
                timeout=60.0  # Longer timeout for tool execution
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Tool executed successfully: {tool_name}")
                return result
            else:
                error_msg = f"Tool call failed with status {response.status_code}"
                logger.error(f"❌ {error_msg}")
                logger.error(f"Response: {response.text}")
                
                return {
                    "error": error_msg,
                    "status_code": response.status_code,
                    "details": response.text
                }
                
        except httpx.TimeoutException:
            return {
                "error": "Tool execution timeout",
                "details": f"Tool '{tool_name}' took too long to execute"
            }
        except Exception as e:
            logger.error(f"❌ Tool call error: {e}", exc_info=True)
            return {
                "error": f"Tool execution failed: {str(e)}",
                "tool_name": tool_name
            }
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names
        
        Returns:
            List of tool names available on this server
        """
        return [tool.get("name", "unknown") for tool in self.tools]
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tool
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool information dictionary or None if not found
        """
        for tool in self.tools:
            if tool.get("name") == tool_name:
                return tool
        return None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with OAuth token
        
        Returns:
            Dictionary of HTTP headers
        """
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    async def close(self):
        """Close the HTTP client and clean up resources"""
        try:
            await self.client.aclose()
            self.connected = False
            logger.info("🔌 Notion MCP client closed")
        except Exception as e:
            logger.error(f"Error closing client: {e}")
    
    def __repr__(self) -> str:
        status = "connected" if self.connected else "disconnected"
        tools_count = len(self.tools)
        return f"<NotionMCPClient status={status} tools={tools_count}>"


# Example usage for testing
async def test_notion_client():
    """Test function to verify Notion MCP client functionality"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # This would come from OAuth flow in production
    access_token = os.getenv("NOTION_ACCESS_TOKEN")
    
    if not access_token:
        print("⚠️ NOTION_ACCESS_TOKEN not found in environment")
        return
    
    # Create and connect client
    client = NotionMCPClient(access_token)
    
    if await client.connect():
        print(f"✅ Connected! Available tools: {client.get_available_tools()}")
        
        # Example: List databases
        result = await client.call_tool("list_databases", {})
        print(f"📊 Databases: {json.dumps(result, indent=2)}")
        
        await client.close()
    else:
        print("❌ Connection failed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_notion_client())
