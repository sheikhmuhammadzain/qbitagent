"""
OpenRouter LLM Integration with Intelligent Tool Calling
Connects MCP tools with OpenRouter's AI models
"""
import json
import logging
from typing import List, Dict, Any, Optional
import aiohttp

from mcp_client_fixed import MCPClient, ToolCall
from config import config

logger = logging.getLogger(__name__)


class LLMAgent:
    """
    AI Agent that uses OpenRouter LLM with MCP tool calling
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

You have access to powerful tools for data querying and analysis. Use them effectively to deliver exceptional value."""
    
    def __init__(self, mcp_client: MCPClient, model: str = "z-ai/glm-4.5-air:free"):
        """
        Initialize LLM Agent
        
        Args:
            mcp_client: Connected MCP client with available tools
            model: OpenRouter model to use (default: glm-4.5-air:free)
        """
        self.mcp_client = mcp_client
        self.model = model
        # Initialize with system prompt
        self.conversation_history: List[Dict[str, Any]] = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
        self.api_key = config.openrouter_api_key
        self.endpoint = config.openrouter_endpoint
        
    async def get_mcp_tools_for_openrouter(self) -> List[Dict[str, Any]]:
        """Convert MCP tools to OpenAI/OpenRouter tool format"""
        try:
            # Get tools from MCP client
            if not self.mcp_client.session:
                return []
            
            tools_result = await self.mcp_client.session.list_tools()
            
            # Convert to OpenRouter format
            openrouter_tools = []
            for tool in tools_result.tools:
                openrouter_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or f"Tool: {tool.name}",
                        "parameters": tool.inputSchema or {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }
                openrouter_tools.append(openrouter_tool)
            
            logger.info(f"Converted {len(openrouter_tools)} MCP tools to OpenRouter format")
            return openrouter_tools
            
        except Exception as e:
            logger.error(f"Error converting MCP tools: {e}")
            return []
    
    async def chat(self, user_message: str) -> tuple[str, List[ToolCall]]:
        """
        Process a chat message with intelligent tool calling
        
        Args:
            user_message: User's input message
            
        Returns:
            tuple: (final_response, list_of_tool_calls)
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Get available tools
        tools = await self.get_mcp_tools_for_openrouter()
        
        # Agentic loop - allow multiple rounds of tool calling
        max_iterations = 10
        all_tool_calls = []
        
        for iteration in range(max_iterations):
            logger.info(f"LLM iteration {iteration + 1}/{max_iterations}")
            
            try:
                # Call OpenRouter API
                response = await self._call_openrouter(
                    messages=self.conversation_history,
                    tools=tools
                )
                
                message = response["choices"][0]["message"]
                
                # Check if LLM wants to call tools
                if message.get("tool_calls"):
                    logger.info(f"LLM requested {len(message['tool_calls'])} tool calls")
                    
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
                        
                        logger.info(f"Executing tool: {function_name} with args: {arguments}")
                        
                        # Execute via MCP client
                        executed_tool = await self.mcp_client.call_tool(function_name, arguments)
                        all_tool_calls.append(executed_tool)
                        
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
                    
                    logger.info(f"LLM completed in {iteration + 1} iterations")
                    return final_response, all_tool_calls
                    
            except Exception as e:
                logger.error(f"Error in LLM iteration {iteration + 1}: {e}")
                error_response = f"I encountered an error: {str(e)}"
                return error_response, all_tool_calls
        
        # Max iterations reached
        logger.warning(f"Reached max iterations ({max_iterations})")
        return "I've completed the analysis with the available information.", all_tool_calls
    
    async def _call_openrouter(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Call OpenRouter API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "MCP Client"
        }
        
        payload = {
            "model": self.model,
            "messages": messages
        }
        
        # Add tools if available
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"  # Let LLM decide when to use tools
        
        logger.debug(f"OpenRouter request: {json.dumps(payload, indent=2)}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OpenRouter API error: {error_text}")
                    raise Exception(f"OpenRouter API error: {response.status} - {error_text}")
                
                result = await response.json()
                logger.debug(f"OpenRouter response: {json.dumps(result, indent=2)}")
                return result
    
    def clear_history(self):
        """Clear conversation history but preserve system prompt"""
        self.conversation_history = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
        logger.info("Conversation history cleared")
