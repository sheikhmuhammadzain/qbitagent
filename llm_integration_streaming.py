"""
Streaming LLM Integration with OpenRouter
Supports real-time streaming responses with tool calling
"""

import httpx
import json
import asyncio
from typing import AsyncIterator, Dict, List, Any, Optional
from mcp_client_fixed import ToolCall as ClientToolCall
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, DEFAULT_MODEL


class StreamingLLMAgent:
    """LLM Agent with streaming support for OpenRouter"""
    
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
    
    def __init__(self, mcp_client, model: str = DEFAULT_MODEL):
        self.mcp_client = mcp_client
        self.model = model
        # Initialize with system prompt
        self.conversation_history: List[Dict[str, Any]] = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
        self.api_key = OPENROUTER_API_KEY
        self.base_url = OPENROUTER_BASE_URL
        
    async def get_mcp_tools_for_openrouter(self) -> List[Dict[str, Any]]:
        """Convert MCP tools to OpenRouter function calling format"""
        if not self.mcp_client or not hasattr(self.mcp_client, 'list_tools'):
            return []
        
        try:
            tools_result = await self.mcp_client.list_tools()
            # tools_result may be a list[Tool] already; if not, adapt.
            tools = []
            if isinstance(tools_result, list):
                tools = tools_result
            elif hasattr(tools_result, 'tools'):
                tools = tools_result.tools
            
            openrouter_tools = []
            for tool in tools:
                name = getattr(tool, 'name', None)
                if not name:
                    continue
                description = getattr(tool, 'description', '') or f"Execute {name}"
                # Parameters: prefer inputSchema, fallback to empty object
                params_schema = {"type": "object", "properties": {}, "required": []}
                if hasattr(tool, 'inputSchema') and getattr(tool, 'inputSchema'):
                    schema = getattr(tool, 'inputSchema')
                    if isinstance(schema, dict):
                        params_schema = schema
                elif hasattr(tool, 'input_schema') and getattr(tool, 'input_schema'):
                    schema = getattr(tool, 'input_schema')
                    if isinstance(schema, dict):
                        params_schema = schema
                
                tool_schema = {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": params_schema,
                    }
                }
                openrouter_tools.append(tool_schema)
            
            return openrouter_tools
            
        except Exception as e:
            print(f"Error getting MCP tools: {e}")
            return []
    
    async def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool via MCP client"""
        try:
            result = await self.mcp_client.call_tool(tool_name, arguments)
            
            # If our client returns ToolCall dataclass, extract the textual result directly
            if isinstance(result, ClientToolCall):
                return result.result

            if hasattr(result, 'content') and result.content:
                content_parts = []
                for item in result.content:
                    if hasattr(item, 'text'):
                        content_parts.append(item.text)
                return "\n".join(content_parts) if content_parts else str(result)
            
            return str(result)
            
        except Exception as e:
            return f"Error executing tool {tool_name}: {str(e)}"
    
    async def chat_stream(self, message: str, max_iterations: int = 100) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream chat with multi-iteration tool calling.
        Loop: stream → collect tool_calls → execute → append results → repeat until no tool calls or cap.
        Yields events: text_chunk, tool_call_start, tool_executing, tool_result, synthesizing, loop_exhausted, done, error
        """
        # 1) Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })

        exhausted = True  # assume we'll exhaust; set to False when we break normally

        try:
            for iteration in range(max_iterations):
                saw_tool_calls = False
                tool_calls: List[Dict[str, Any]] = []
                assistant_message = ""
                reasoning_content = ""  # Track reasoning content

                # 2) Prepare payload for this iteration
                tools = await self.get_mcp_tools_for_openrouter()
                payload = {
                    "model": self.model,
                    "messages": self.conversation_history,
                    "stream": True,
                    "temperature": 0.7,
                    "max_tokens": 12000,
                    "reasoning": {"enabled": True}  # Enable reasoning tokens
                }
                if tools:
                    payload["tools"] = tools
                    payload["tool_choice"] = "auto"

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "MCP Database Assistant",
                }

                # 3) Stream this iteration with retry logic for rate limits
                max_retries = 3
                retry_delay = 2  # Start with 2 seconds
                
                for retry_attempt in range(max_retries):
                    try:
                        async with httpx.AsyncClient(timeout=60.0) as client:
                            async with client.stream(
                                "POST",
                                f"{self.base_url}/chat/completions",
                                json=payload,
                                headers=headers,
                            ) as response:
                                # Handle rate limiting (429)
                                if response.status_code == 429:
                                    if retry_attempt < max_retries - 1:
                                        wait_time = retry_delay * (2 ** retry_attempt)
                                        yield {
                                            "type": "rate_limit",
                                            "message": f"Rate limit hit. Retrying in {wait_time}s... (attempt {retry_attempt + 1}/{max_retries})",
                                            "retry_in": wait_time,
                                        }
                                        await asyncio.sleep(wait_time)
                                        continue  # Retry
                                    else:
                                        error_text = await response.aread()
                                        yield {
                                            "type": "error",
                                            "error": f"Rate limit exceeded after {max_retries} retries. Please wait a moment and try again.",
                                        }
                                        return
                                
                                # Handle other errors
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
                                        
                                        # Handle reasoning summary
                                        if "reasoning_details" in delta:
                                            details = delta["reasoning_details"]
                                            if "summary" in details:
                                                yield {"type": "reasoning_summary", "summary": details["summary"]}
                                            if "encrypted" in details and details["encrypted"]:
                                                yield {"type": "reasoning_encrypted", "encrypted": True}

                                        # Stream text until a tool call is requested
                                        if ("content" in delta) and delta["content"] and not saw_tool_calls:
                                            assistant_message += delta["content"]
                                            yield {"type": "text_chunk", "content": delta["content"]}

                                        # Collect tool calls and streamed arguments
                                        if "tool_calls" in delta:
                                            saw_tool_calls = True
                                            for tc in delta["tool_calls"]:
                                                tid = tc.get("id")
                                                name = tc.get("function", {}).get("name", "")
                                                args_part = tc.get("function", {}).get("arguments", "")

                                                # Start a new tool call when we see an id first time
                                                if tid and not any(c.get("id") == tid for c in tool_calls):
                                                    tool_calls.append({
                                                        "id": tid,
                                                        "type": "function",
                                                        "function": {"name": name, "arguments": ""},
                                                    })
                                                    yield {"type": "tool_call_start", "tool_name": name, "tool_id": tid}

                                                # Accumulate streamed arguments
                                                if tid and args_part:
                                                    for c in tool_calls:
                                                        if c.get("id") == tid:
                                                            c["function"]["arguments"] += args_part
                                    except json.JSONDecodeError:
                                        continue
                        
                        # If we got here, the request succeeded - break retry loop
                        break
                        
                    except httpx.ReadTimeout:
                        if retry_attempt < max_retries - 1:
                            yield {
                                "type": "timeout",
                                "message": f"Request timeout. Retrying... (attempt {retry_attempt + 1}/{max_retries})",
                            }
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            yield {"type": "error", "error": "Request timeout after retries"}
                            return

                # 4) If this iteration requested tools, execute them and loop again
                if saw_tool_calls and tool_calls:
                    # Add assistant turn (with tool_calls) to history
                    assistant_turn = {
                        "role": "assistant",
                        "content": assistant_message if assistant_message else None,
                        "tool_calls": tool_calls,
                    }
                    # Include reasoning content if present
                    if reasoning_content:
                        assistant_turn["reasoning"] = reasoning_content
                    self.conversation_history.append(assistant_turn)

                    # Execute each tool, add tool outputs to history
                    for tc in tool_calls:
                        tool_name = tc["function"]["name"]
                        try:
                            args = json.loads(tc["function"].get("arguments") or "{}")
                        except json.JSONDecodeError:
                            args = {}

                        yield {"type": "tool_executing", "tool_name": tool_name, "arguments": args}
                        result = await self.execute_tool_call(tool_name, args)
                        yield {"type": "tool_result", "tool_name": tool_name, "result": result}

                        self.conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": tool_name,
                            "content": result,
                        })

                    # Hint to UI and continue loop
                    yield {"type": "synthesizing", "message": "Synthesizing next step..."}
                    continue

                # 5) No tool calls this turn → finalize and stop looping
                if assistant_message:
                    assistant_turn = {"role": "assistant", "content": assistant_message}
                    # Include reasoning content if present
                    if reasoning_content:
                        assistant_turn["reasoning"] = reasoning_content
                    self.conversation_history.append(assistant_turn)
                exhausted = False
                break

            # 6) If we hit the iteration cap, notify the UI
            if exhausted:
                yield {"type": "loop_exhausted", "message": "Reached max tool-calling iterations"}

            yield {"type": "done"}

        except Exception as e:
            yield {"type": "error", "error": str(e)}
    
    async def _stream_final_response(self) -> AsyncIterator[Dict[str, Any]]:
        """Stream the final response after tool execution"""
        tools = await self.get_mcp_tools_for_openrouter()
        
        payload = {
            "model": self.model,
            "messages": self.conversation_history,
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 12000
        }
        
        if tools:
            payload["tools"] = tools
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "MCP Database Assistant"
        }
        
        assistant_message = ""
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                ) as response:
                    
                    async for line in response.aiter_lines():
                        if not line or line.strip() == "":
                            continue
                        
                        if line.startswith("data: "):
                            data_str = line[6:]
                            
                            if data_str.strip() == "[DONE]":
                                break
                            
                            try:
                                chunk_data = json.loads(data_str)
                                choice = chunk_data.get("choices", [{}])[0]
                                delta = choice.get("delta", {})
                                
                                if "content" in delta and delta["content"]:
                                    content = delta["content"]
                                    assistant_message += content
                                    yield {
                                        "type": "text_chunk",
                                        "content": content
                                    }
                            
                            except json.JSONDecodeError:
                                continue
            
            # Save final assistant message
            if assistant_message:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })
        
        except Exception as e:
            yield {
                "type": "error",
                "error": f"Error in final response: {str(e)}"
            }
    
    def clear_history(self):
        """Clear conversation history but preserve system prompt"""
        self.conversation_history = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return self.conversation_history
