"""
Fixed MCP Client for FastAPI
Based on official MCP Python SDK patterns
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl
import mcp.types as types

logger = logging.getLogger(__name__)

@dataclass
class ToolCall:
    """Represents a tool call made during conversation"""
    tool_name: str
    arguments: Dict[str, Any]
    result: str
    timestamp: datetime
    duration_ms: float


class MCPClient:
    """
    Simplified MCP Client for FastAPI integration
    Based on official MCP Python SDK patterns
    """
    
    def __init__(self, server_params: StdioServerParameters):
        """Initialize with server parameters"""
        self.server_params = server_params
        self.session: Optional[ClientSession] = None
        self._stdio_context = None
        self._read_stream = None
        self._write_stream = None
        
    async def connect(self) -> None:
        """Connect to MCP server"""
        try:
            logger.info(f"Connecting to MCP server: {self.server_params.command}")
            
            # Create stdio client context
            self._stdio_context = stdio_client(self.server_params)
            self._read_stream, self._write_stream = await self._stdio_context.__aenter__()
            
            logger.info("Stdio transport established")
            
            # Create client session
            self.session = ClientSession(self._read_stream, self._write_stream)
            await self.session.__aenter__()
            
            logger.info("Client session created")
            
            # Initialize the connection
            await self.session.initialize()
            
            logger.info("Successfully connected and initialized MCP session")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            await self.close()
            raise
    
    async def list_tools(self) -> List[types.Tool]:
        """List available tools (full objects)"""
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")
        
        try:
            tools_result = await self.session.list_tools()
            # Return full Tool objects for richer metadata (name, description, input schema)
            return list(tools_result.tools)
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolCall:
        """Execute a tool and return ToolCall object"""
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")
        
        start_time = datetime.now()
        
        try:
            logger.info(f"Calling tool '{tool_name}' with arguments: {arguments}")
            
            result = await self.session.call_tool(tool_name, arguments)
            
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            # Extract result text
            result_text = ""
            try:
                # Prefer structuredContent when present (chart specs etc.)
                if getattr(result, "structuredContent", None):
                    import json as _json
                    result_text = _json.dumps(result.structuredContent, indent=2)
                elif getattr(result, "content", None):
                    for content in result.content:
                        if isinstance(content, types.TextContent):
                            result_text += content.text
                else:
                    result_text = str(result)
            except Exception:
                result_text = str(result)
            
            tool_call = ToolCall(
                tool_name=tool_name,
                arguments=arguments,
                result=result_text,
                timestamp=start_time,
                duration_ms=duration_ms
            )
            
            logger.info(f"Tool '{tool_name}' executed in {duration_ms:.2f}ms")
            return tool_call
            
        except Exception as e:
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            error_msg = f"Error executing tool '{tool_name}': {str(e)}"
            logger.error(error_msg)
            
            return ToolCall(
                tool_name=tool_name,
                arguments=arguments,
                result=f'{{"error": "{error_msg}"}}',
                timestamp=start_time,
                duration_ms=duration_ms
            )
    
    async def close(self) -> None:
        """Close the connection"""
        try:
            logger.info("Closing MCP client connection...")
            
            if self.session:
                try:
                    await self.session.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"Error closing session: {e}")
                self.session = None
            
            if self._stdio_context:
                try:
                    await self._stdio_context.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"Error closing stdio context: {e}")
                self._stdio_context = None
            
            self._read_stream = None
            self._write_stream = None
            
            logger.info("MCP client closed successfully")
            
        except Exception as e:
            logger.error(f"Error during close: {e}")


class MCPServerConfig:
    """MCP Server configurations"""
    
    @staticmethod
    def get_configs() -> Dict[str, StdioServerParameters]:
        """Get predefined server configurations"""
        return {
            "SQLite": StdioServerParameters(
                command="python",
                args=["sqlite_mcp_fastmcp.py", "example.db"],
                env=None
            ),
            "Filesystem": StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "."],
                env=None
            ),
            "Notes": StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-notes", "--notes-dir", "./notes"],
                env=None
            ),
            "Git": StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-git", "--repository", "."],
                env=None
            )
        }
    
    @staticmethod
    def get_available_models() -> List[str]:
        """Get list of available OpenRouter models"""
        return [
            "z-ai/glm-4.5-air:free",
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4-turbo",
            "google/gemini-pro",
        ]
