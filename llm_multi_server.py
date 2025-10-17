"""
Multi-Server LLM Agent
Supports simultaneous connections to multiple MCP servers (SQLite, Notion, etc.)
"""
import json
import logging
from typing import List, Dict, Any, Optional
import aiohttp

from config import config

logger = logging.getLogger(__name__)


class MultiServerLLMAgent:
    """
    AI Agent that uses OpenRouter LLM with multiple MCP servers
    
    This agent can route tool calls to different MCP servers (SQLite, Notion, etc.)
    based on the tool name, allowing users to work with multiple data sources
    in a single conversation.
    """
    
    # System prompt defining the agent's identity and capabilities
    SYSTEM_PROMPT = """You are Qbit Data Agent, built by Zain Sheikh. You are an expert data analyst specializing in:

1. **Data Analysis Excellence:**
   - Thorough exploration and understanding of datasets
   - Statistical analysis and pattern recognition
   - Data quality assessment and anomaly detection

2. **Prescriptive Analytics:**
   - Actionable recommendations based on data insights
   - Strategic suggestions for business improvement
   - Risk assessment and mitigation strategies

3. **Communication:**
   - Clear, concise explanations of complex data findings
   - Data-driven storytelling
   - Visual and narrative presentation of insights

4. **Data Visualization:**
   IMPORTANT: When users request charts or visualizations, you MUST use the following JSON format.
   DO NOT use SVG, base64 images, or markdown image syntax.
   
   Use this exact format:
   ```
   <chart type="bar" x="column_name" y="value_column">
   { "type": "chart", "spec": { "chart": "bar", "x": "column_name", "y": "value_column", "data": [ { "column_name": "Value1", "value_column": 123 }, { "column_name": "Value2", "value_column": 456 } ] } }
   </chart>
   ```
   
   Supported chart types: "bar", "line", "area", "pie"
   Always include the complete data array with actual values from your query results.
   
   NEVER use:
   - ![Chart](data:image/svg+xml;base64,...)
   - SVG elements directly
   - Any base64-encoded images

Your approach:
- Always start by understanding the data structure and quality
- Perform comprehensive analysis before drawing conclusions
- Provide specific, actionable recommendations
- Support insights with relevant data points
- Be proactive in identifying opportunities and risks
- Create visualizations when they enhance understanding

You have access to powerful tools for data querying and analysis across multiple data sources (databases, Notion workspaces, web search). Use them effectively to deliver exceptional value."""
    
    def __init__(self, model: str = "z-ai/glm-4.5-air:free"):
        """
        Initialize Multi-Server LLM Agent
        
        Args:
            model: OpenRouter model to use (default: glm-4.5-air:free)
        """
        self.model = model
        # Initialize with system prompt
        self.conversation_history: List[Dict[str, Any]] = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
        self.api_key = config.openrouter_api_key
        self.endpoint = config.openrouter_endpoint
        
        # Registry of MCP clients
        self.mcp_clients: Dict[str, Any] = {}  # server_name -> client instance
        self.tool_routing: Dict[str, str] = {}  # tool_name -> server_name
        
    def register_mcp_client(self, server_name: str, client: Any):
        """
        Register an MCP client (SQLite, Notion, etc.)
        
        Args:
            server_name: Identifier for the server (e.g., "SQLite", "Notion_workspace123")
            client: MCP client instance (MCPClient or NotionMCPClient)
        """
        self.mcp_clients[server_name] = client
        
        # Update tool routing
        tools = self._get_tools_from_client(client)
        for tool in tools:
            tool_name = tool.get('name', '')
            if tool_name:
                self.tool_routing[tool_name] = server_name
        
        logger.info(f"✅ Registered '{server_name}' with {len(tools)} tools")
    
    def _get_tools_from_client(self, client: Any) -> List[Dict[str, Any]]:
        """Extract tools from a client (supports both MCPClient and NotionMCPClient)"""
        # For NotionMCPClient
        if hasattr(client, 'tools') and isinstance(client.tools, list):
            return client.tools
        
        # For MCPClient - we'll handle this during async calls
        return []
    
    async def get_all_tools_for_openrouter(self) -> List[Dict[str, Any]]:
        """
        Convert all registered MCP tools to OpenAI/OpenRouter tool format
        
        Returns:
            List of tools in OpenRouter format
        """
        all_tools = []
        
        for server_name, client in self.mcp_clients.items():
            try:
                # Handle NotionMCPClient and WebSearchClient
                if hasattr(client, 'tools') and isinstance(client.tools, list):
                    logger.info(f"  📋 Processing {len(client.tools)} tools from {server_name} (client.tools)")
                    for tool in client.tools:
                        # Support both input_schema and inputSchema
                        input_schema = tool.get('inputSchema') or tool.get('input_schema', {
                            "type": "object",
                            "properties": {},
                            "required": []
                        })
                        
                        openrouter_tool = {
                            "type": "function",
                            "function": {
                                "name": tool.get('name', ''),
                                "description": tool.get('description', f"Tool from {server_name}"),
                                "parameters": input_schema
                            }
                        }
                        all_tools.append(openrouter_tool)
                        logger.debug(f"    ✓ Added tool: {tool.get('name', 'unknown')} from {server_name}")
                        
                        # Update routing
                        tool_name = tool.get('name', '')
                        if tool_name:
                            self.tool_routing[tool_name] = server_name
                
                # Handle MCPClient (SQLite)
                elif hasattr(client, 'session') and client.session:
                    tools_result = await client.session.list_tools()
                    logger.info(f"  📊 Processing {len(tools_result.tools)} tools from {server_name} (MCPClient)")
                    
                    for tool in tools_result.tools:
                        openrouter_tool = {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description or f"Tool from {server_name}",
                                "parameters": tool.inputSchema or {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                }
                            }
                        }
                        all_tools.append(openrouter_tool)
                        logger.debug(f"    ✓ Added tool: {tool.name} from {server_name}")
                        
                        # Update routing
                        self.tool_routing[tool.name] = server_name
                
                else:
                    logger.warning(f"⚠️ Cannot extract tools from {server_name}")
                    
            except Exception as e:
                logger.error(f"❌ Error getting tools from {server_name}: {e}")
        
        logger.info(f"📦 Collected {len(all_tools)} tools from {len(self.mcp_clients)} servers")
        return all_tools
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Route and execute a tool call to the correct MCP server
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        server_name = self.tool_routing.get(tool_name)
        
        if not server_name:
            error_msg = f"Unknown tool: {tool_name}"
            logger.error(f"❌ {error_msg}")
            return type('ToolResult', (), {'result': json.dumps({"error": error_msg})})()
        
        client = self.mcp_clients.get(server_name)
        if not client:
            error_msg = f"Server not connected: {server_name}"
            logger.error(f"❌ {error_msg}")
            return type('ToolResult', (), {'result': json.dumps({"error": error_msg})})()
        
        try:
            logger.info(f"🔧 Executing '{tool_name}' on '{server_name}'")
            
            # Handle NotionMCPClient
            if hasattr(client, 'call_tool'):
                result = await client.call_tool(tool_name, arguments)
                # Wrap result in a ToolCall-like object
                return type('ToolResult', (), {'result': json.dumps(result)})()
            
            # Handle MCPClient
            elif hasattr(client, 'call_tool'):
                return await client.call_tool(tool_name, arguments)
            
            else:
                error_msg = f"Client {server_name} doesn't support call_tool"
                logger.error(f"❌ {error_msg}")
                return type('ToolResult', (), {'result': json.dumps({"error": error_msg})})()
                
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return type('ToolResult', (), {'result': json.dumps({"error": error_msg})})()
    
    async def chat(self, user_message: str) -> Dict[str, Any]:
        """
        Process a chat message with intelligent multi-server tool calling
        
        Args:
            user_message: User's input message
            
        Returns:
            Dictionary containing:
                - content: Final response string
                - tool_calls: List of tool calls made
                - servers_used: List of server names used
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Get available tools from all servers
        tools = await self.get_all_tools_for_openrouter()
        
        # Agentic loop - allow multiple rounds of tool calling
        max_iterations = 100
        all_tool_calls = []
        servers_used = set()
        
        for iteration in range(max_iterations):
            logger.info(f"🔄 LLM iteration {iteration + 1}/{max_iterations}")
            
            try:
                # Call OpenRouter API
                response = await self._call_openrouter(
                    messages=self.conversation_history,
                    tools=tools
                )
                
                message = response["choices"][0]["message"]
                
                # Check if LLM wants to call tools
                if message.get("tool_calls"):
                    logger.info(f"📞 LLM requested {len(message['tool_calls'])} tool calls")
                    
                    # Add assistant message with tool calls
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": message.get("content"),
                        "tool_calls": message["tool_calls"]
                    })
                    
                    # Execute each tool call
                    for tool_call in message["tool_calls"]:
                        function_name = tool_call["function"]["name"]
                        try:
                            arguments = json.loads(tool_call["function"]["arguments"])
                        except json.JSONDecodeError:
                            arguments = {}
                        
                        # Execute via appropriate MCP client
                        executed_tool = await self.execute_tool(function_name, arguments)
                        all_tool_calls.append({
                            "tool": function_name,
                            "server": self.tool_routing.get(function_name, "unknown"),
                            "arguments": arguments,
                            "result": executed_tool.result
                        })
                        
                        # Track which servers were used
                        if function_name in self.tool_routing:
                            servers_used.add(self.tool_routing[function_name])
                        
                        # Add tool result to conversation
                        self.conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": executed_tool.result
                        })
                    
                    # Continue loop to let LLM process tool results
                    continue
                
                else:
                    # No tool calls - LLM has final response
                    final_response = message.get("content", "")
                    
                    # Add to history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": final_response
                    })
                    
                    logger.info(f"✅ LLM completed in {iteration + 1} iterations")
                    return {
                        "content": final_response,
                        "tool_calls": all_tool_calls,
                        "servers_used": list(servers_used)
                    }
                    
            except Exception as e:
                logger.error(f"❌ Error in LLM iteration {iteration + 1}: {e}", exc_info=True)
                error_response = f"I encountered an error: {str(e)}"
                return {
                    "content": error_response,
                    "tool_calls": all_tool_calls,
                    "servers_used": list(servers_used)
                }
        
        # Max iterations reached
        logger.warning(f"⚠️ Reached max iterations ({max_iterations})")
        return {
            "content": "I've completed the analysis with the available information.",
            "tool_calls": all_tool_calls,
            "servers_used": list(servers_used)
        }
    
    async def _call_openrouter(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Call OpenRouter API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "MCP Multi-Server Client"
        }
        
        payload = {
            "model": self.model,
            "messages": messages
        }
        
        # Add tools if available
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"  # Let LLM decide when to use tools
        
        logger.debug(f"📤 OpenRouter request: {len(messages)} messages, {len(tools)} tools")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ OpenRouter API error: {error_text}")
                    raise Exception(f"OpenRouter API error: {response.status} - {error_text}")
                
                result = await response.json()
                return result
    
    def clear_history(self):
        """Clear conversation history but preserve system prompt"""
        self.conversation_history = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
        logger.info("🗑️ Conversation history cleared")
    
    def get_registered_servers(self) -> List[str]:
        """Get list of registered server names"""
        return list(self.mcp_clients.keys())
    
    def __repr__(self) -> str:
        servers = ", ".join(self.mcp_clients.keys())
        tools_count = len(self.tool_routing)
        return f"<MultiServerLLMAgent servers=[{servers}] tools={tools_count}>"
