"""
Streaming Multi-Server LLM Agent
Supports real-time streaming with tool calling across multiple MCP servers
"""
import httpx
import json
import asyncio
import logging
from typing import AsyncIterator, Dict, List, Any, Optional

from config import config

logger = logging.getLogger(__name__)


class StreamingMultiServerLLMAgent:
    """
    Streaming LLM Agent with multi-server MCP support
    
    Features:
    - Real-time streaming responses
    - Reasoning tokens support
    - Multiple MCP servers (SQLite, Notion, WebSearch)
    - Automatic tool routing
    - Agentic loop with iterative tool calling
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
   CRITICAL: When users ask for charts, you MUST embed them INLINE in your response using this exact format.
   DO NOT use any render_chart or similar tools. DO NOT use SVG, base64 images, or markdown syntax.
   
   MANDATORY INLINE CHART FORMAT:
   ```
   <chart type="bar" x="column_name" y="value_column">
   { "type": "chart", "spec": { "chart": "bar", "x": "column_name", "y": "value_column", "data": [ { "column_name": "Value1", "value_column": 123 }, { "column_name": "Value2", "value_column": 456 } ] } }
   </chart>
   ```
   
   WORKFLOW:
   1. Use SQL tools (execute_query) to get the data
   2. Format the query result into the data array
   3. Embed the <chart> block INLINE in your final response
   4. Add brief explanatory text above/below the chart
   
   Supported: "bar", "line", "area", "pie"
   NEVER use render_chart tool or similar - inline charts only!

Your approach:
- Always start by understanding the data structure and quality
- Perform comprehensive analysis before drawing conclusions
- Provide specific, actionable recommendations
- Support insights with relevant data points
- Be proactive in identifying opportunities and risks
- Create visualizations when they enhance understanding

You have access to powerful tools for data querying and analysis across multiple data sources (databases, Notion workspaces, web search). Use them effectively to deliver exceptional value."""
    
    def __init__(self, model: str = "z-ai/glm-4.5-air:free"):
        """Initialize Streaming Multi-Server Agent
        
        Args:
            model: OpenRouter model to use
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
        """Register an MCP client
        
        Args:
            server_name: Server identifier (e.g., "SQLite", "Notion_workspace", "WebSearch")
            client: MCP client instance
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
        """Extract tools from a client"""
        if hasattr(client, 'tools') and isinstance(client.tools, list):
            return client.tools
        return []
    
    async def get_all_tools_for_openrouter(self) -> List[Dict[str, Any]]:
        """Get all tools in OpenRouter format"""
        all_tools = []
        
        for server_name, client in self.mcp_clients.items():
            try:
                # Handle clients with direct tools list (NotionAPIClient, WebSearchClient)
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
                        self.tool_routing[tool.get('name', '')] = server_name
                
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
                        self.tool_routing[tool.name] = server_name
                        
            except Exception as e:
                logger.error(f"❌ Error getting tools from {server_name}: {e}")
        
        logger.info(f"📦 Collected {len(all_tools)} tools from {len(self.mcp_clients)} servers")
        return all_tools
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool on the appropriate server
        
        Args:
            tool_name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool result as string
        """
        server_name = self.tool_routing.get(tool_name)
        
        if not server_name:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        
        client = self.mcp_clients.get(server_name)
        if not client:
            return json.dumps({"error": f"Server not connected: {server_name}"})
        
        try:
            logger.info(f"🔧 Executing '{tool_name}' on '{server_name}'")
            
            # Handle clients with call_tool method
            if hasattr(client, 'call_tool'):
                result = await client.call_tool(tool_name, arguments)
                
                # If result is dict, serialize it
                if isinstance(result, dict):
                    return json.dumps(result)
                # If it's a ToolCall object, extract result
                elif hasattr(result, 'result'):
                    return result.result
                # Otherwise convert to string
                return str(result)
            
            # Handle MCPClient (SQLite)
            elif hasattr(client, 'call_tool'):
                result = await client.call_tool(tool_name, arguments)
                if hasattr(result, 'result'):
                    return result.result
                return str(result)
            
            else:
                return json.dumps({"error": f"Client {server_name} doesn't support call_tool"})
                
        except Exception as e:
            logger.error(f"❌ Tool execution failed: {e}", exc_info=True)
            return json.dumps({"error": f"Tool execution failed: {str(e)}"})
    
    async def chat_stream(self, message: str, max_iterations: int = 100) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream chat with multi-iteration tool calling across multiple servers
        
        Args:
            message: User message
            max_iterations: Max tool-calling iterations
            
        Yields:
            Stream events: text_chunk, tool_call_start, tool_executing, tool_result, 
                          reasoning_chunk, synthesizing, done, error
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        
        try:
            for iteration in range(max_iterations):
                saw_tool_calls = False
                tool_calls: List[Dict[str, Any]] = []
                assistant_message = ""
                reasoning_content = ""
                
                # Get tools
                tools = await self.get_all_tools_for_openrouter()
                
                # Prepare payload
                payload = {
                    "model": self.model,
                    "messages": self.conversation_history,
                    "stream": True,
                    "temperature": 0.7,
                    "max_tokens": 12000,
                    "reasoning": {"enabled": True}
                }
                
                if tools:
                    payload["tools"] = tools
                    payload["tool_choice"] = "auto"
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "MCP Multi-Server Assistant",
                }
                
                # Stream this iteration
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream(
                        "POST",
                        self.endpoint,
                        json=payload,
                        headers=headers,
                    ) as response:
                        
                        if response.status_code != 200:
                            error_text = await response.aread()
                            yield {
                                "type": "error",
                                "error": f"API Error {response.status_code}: {error_text.decode()}",
                            }
                            return
                        
                        async for line in response.aiter_lines():
                            if not line or line.strip() == "":
                                continue
                            if not line.startswith("data: "):
                                continue
                            
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            
                            try:
                                chunk = json.loads(data_str)
                                choice = chunk.get("choices", [{}])[0]
                                delta = choice.get("delta", {})
                                
                                # Handle reasoning tokens
                                if "reasoning" in delta and delta["reasoning"]:
                                    reasoning_chunk = delta["reasoning"]
                                    reasoning_content += reasoning_chunk
                                    yield {"type": "reasoning_chunk", "content": reasoning_chunk}
                                
                                # Handle content
                                if "content" in delta and delta["content"]:
                                    content_chunk = delta["content"]
                                    assistant_message += content_chunk
                                    yield {"type": "text_chunk", "content": content_chunk}
                                
                                # Handle tool calls
                                if "tool_calls" in delta and delta["tool_calls"]:
                                    saw_tool_calls = True
                                    for tc_delta in delta["tool_calls"]:
                                        idx = tc_delta.get("index", 0)
                                        
                                        # Extend tool_calls list if needed
                                        while len(tool_calls) <= idx:
                                            tool_calls.append({
                                                "id": "",
                                                "type": "function",
                                                "function": {"name": "", "arguments": ""}
                                            })
                                        
                                        # Update tool call data
                                        if "id" in tc_delta:
                                            tool_calls[idx]["id"] = tc_delta["id"]
                                        
                                        if "function" in tc_delta:
                                            func = tc_delta["function"]
                                            if "name" in func:
                                                tool_calls[idx]["function"]["name"] = func["name"]
                                                # Emit tool_call_start event
                                                yield {
                                                    "type": "tool_call_start",
                                                    "tool_name": func["name"]
                                                }
                                            if "arguments" in func:
                                                tool_calls[idx]["function"]["arguments"] += func["arguments"]
                                
                            except json.JSONDecodeError:
                                continue
                
                # Process tool calls if any
                if saw_tool_calls and tool_calls:
                    logger.info(f"📞 Executing {len(tool_calls)} tool calls")
                    
                    # Add assistant message with tool calls to history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": assistant_message or None,
                        "tool_calls": tool_calls
                    })
                    
                    # Execute each tool
                    for tool_call in tool_calls:
                        function_name = tool_call["function"]["name"]
                        
                        try:
                            arguments = json.loads(tool_call["function"]["arguments"])
                        except json.JSONDecodeError:
                            arguments = {}
                        
                        # Emit tool_executing event
                        yield {
                            "type": "tool_executing",
                            "tool_name": function_name,
                            "arguments": arguments
                        }
                        
                        # Execute tool
                        result = await self.execute_tool(function_name, arguments)
                        
                        # Emit tool_result event
                        yield {
                            "type": "tool_result",
                            "tool_name": function_name,
                            "result": result[:200]  # Preview only
                        }
                        
                        # Add tool result to history
                        self.conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result
                        })
                    
                    # Emit synthesizing event
                    yield {
                        "type": "synthesizing",
                        "message": "Synthesizing response..."
                    }
                    
                    # Continue loop to let LLM process results
                    continue
                
                else:
                    # No tool calls - done
                    if assistant_message:
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": assistant_message
                        })
                    
                    yield {"type": "done"}
                    return
            
            # Max iterations reached
            yield {"type": "done"}
            
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e)
            }
    
    def clear_history(self):
        """Clear conversation history but preserve system prompt"""
        self.conversation_history = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
        logger.info("🗑️ Conversation history cleared")
