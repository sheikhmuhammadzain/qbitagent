"""
Fixed FastAPI backend for MCP Client
Uses proper MCP SDK patterns based on official documentation
"""
import asyncio
import json
import logging
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime

# Fix for Windows: Set ProactorEventLoop policy to support subprocesses
# NOTE: Must happen BEFORE FastAPI imports, so we use print() not logger
if sys.platform == 'win32':
    # Check current loop and policy
    current_policy = asyncio.get_event_loop_policy()
    print(f"🔧 Windows detected - Current event loop policy: {type(current_policy).__name__}")
    
    # Set the correct policy
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("✅ Set WindowsProactorEventLoopPolicy")
    
    # Try to get or create a new loop with the correct policy
    try:
        loop = asyncio.get_event_loop()
        print(f"🔍 Current event loop type: {type(loop).__name__}")
        
        # If it's the wrong loop type, close it and create a new one
        if not isinstance(loop, asyncio.ProactorEventLoop):
            print(f"⚠️ Wrong event loop type ({type(loop).__name__}), recreating...")
            if not loop.is_closed():
                loop.close()
            # Create new ProactorEventLoop
            new_loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(new_loop)
            print(f"✅ Created new ProactorEventLoop: {type(new_loop).__name__}")
        else:
            print(f"✅ Already using ProactorEventLoop - subprocess support enabled")
    except RuntimeError as e:
        print(f"⚠️ Could not get event loop: {e}, creating new one...")
        # Create a new one
        new_loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(new_loop)
        print(f"✅ Created new ProactorEventLoop: {type(new_loop).__name__}")
    print("=" * 80)

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
import os
import uuid
import shutil
from pathlib import Path

from mcp_client_fixed import MCPClient, MCPServerConfig, ToolCall
import sys
from mcp import StdioServerParameters
from llm_integration import LLMAgent
from llm_integration_streaming import StreamingLLMAgent
from llm_multi_server import MultiServerLLMAgent
from data_pipeline import DataPipeline
from config import (
    DEFAULT_MODEL,
    NOTION_CLIENT_ID,
    NOTION_CLIENT_SECRET,
    NOTION_REDIRECT_URI,
    NOTION_OAUTH_URL,
    NOTION_TOKEN_URL,
    NOTION_API_VERSION
)
from notion_api_client import NotionAPIClient
from web_search_client import WebSearchClient
import httpx

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="MCP Client API (Fixed)",
    description="REST API for MCP Client with proper SDK integration",
    version="2.0.0"
)

# Add CORS middleware
# Get allowed origins from environment or use defaults
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://103.18.20.205:8091,http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware (cookie-based sessions)
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-secret-change-me")
if SESSION_SECRET == "dev-secret-change-me":
    logger.warning("⚠️  Using default session secret! Set SESSION_SECRET environment variable for production.")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, max_age=60 * 60 * 24 * 7)

# Per-user client and agent instances
user_clients: dict[str, MCPClient] = {}
user_agents: dict[str, LLMAgent] = {}
user_stream_agents: dict[str, StreamingLLMAgent] = {}
user_locks: dict[str, asyncio.Lock] = {}

# Per-user Notion API clients
user_notion_clients: dict[str, Dict[str, NotionAPIClient]] = {}

# Global web search client (shared across all users)
web_search_client: Optional[WebSearchClient] = None

def get_lock_for_user(username: str) -> asyncio.Lock:
    if username not in user_locks:
        user_locks[username] = asyncio.Lock()
    return user_locks[username]

# --- Minimal Auth + Chat History (SQLite) ---
APP_DB_PATH = os.environ.get("APP_DB_PATH", "server.db")

async def init_app_db():
    import aiosqlite
    async with aiosqlite.connect(APP_DB_PATH) as db:
        # Users table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT UNIQUE NOT NULL,
              password_hash TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )
        # Chat messages table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL,
              session_id TEXT NOT NULL,
              role TEXT NOT NULL,
              content TEXT,
              metadata TEXT,
              created_at TEXT NOT NULL
            );
            """
        )
        # Notion OAuth tokens table
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS notion_tokens (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL,
              access_token TEXT NOT NULL,
              workspace_id TEXT NOT NULL,
              workspace_name TEXT,
              workspace_icon TEXT,
              bot_id TEXT,
              created_at TEXT NOT NULL,
              UNIQUE(username, workspace_id)
            );
            """
        )
        await db.commit()
        logger.info("✅ Database initialized successfully")

def hash_password(pw: str) -> str:
    import hashlib
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def require_user(request: Request) -> str:
    """Get current authenticated user or raise 401"""
    username = request.session.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Authentication required")
    return username

def get_user_or_anonymous(request: Request) -> str:
    """Get current user or return anonymous for public endpoints"""
    username = request.session.get("username")
    if not username:
        # For public endpoints, return anonymous user
        username = "anonymous"
        request.session["username"] = username
        request.session["session_id"] = str(uuid.uuid4())
    return username

def get_pipeline(username: str) -> DataPipeline:
    # separate storage per user
    return DataPipeline(upload_dir=str(Path("uploads") / username))

async def hydrate_agent_if_empty(username: str, session_id: str, agent) -> None:
    """If the agent has no in-memory history (e.g., new process), hydrate from DB.
    Loads the last 40 messages for the current session (user/assistant only).
    Preserves system prompt if present."""
    if not hasattr(agent, "conversation_history"):
        return
    
    # Check if history has more than just system prompt
    history = getattr(agent, "conversation_history", [])
    has_system_prompt = len(history) > 0 and history[0].get("role") == "system"
    has_other_messages = len(history) > (1 if has_system_prompt else 0)
    
    # Only hydrate if we don't have chat messages (but may have system prompt)
    if has_other_messages:
        return
    
    try:
        import aiosqlite
        rows = []
        async with aiosqlite.connect(APP_DB_PATH) as db:
            async with db.execute(
                "SELECT role, content FROM messages WHERE username = ? AND session_id = ? ORDER BY id DESC LIMIT 40",
                (username, session_id),
            ) as cur:
                rows = await cur.fetchall()
        # reverse to chronological and append after system prompt
        for role, content in reversed(rows):
            if role in ("user", "assistant"):
                agent.conversation_history.append({"role": role, "content": content or ""})
    except Exception as e:
        logger.warning(f"Failed to hydrate memory: {e}")

# Request/Response Models
class ConnectRequest(BaseModel):
    server_name: str
    # Model is now locked to config DEFAULT_MODEL, not user-configurable

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    tool_calls: List[Dict[str, Any]]
    timestamp: str
class AuthRequest(BaseModel):
    username: str
    password: str

@app.on_event("startup")
async def on_startup():
    global web_search_client
    
    # Diagnostic: Check event loop type on Windows
    if sys.platform == 'win32':
        loop = asyncio.get_event_loop()
        loop_type = type(loop).__name__
        policy = type(asyncio.get_event_loop_policy()).__name__
        logger.info(f"🔍 Event Loop Diagnostics:")
        logger.info(f"   Policy: {policy}")
        logger.info(f"   Loop Type: {loop_type}")
        logger.info(f"   Is ProactorEventLoop: {isinstance(loop, asyncio.ProactorEventLoop)}")
        
        if not isinstance(loop, asyncio.ProactorEventLoop):
            logger.error(f"❌ CRITICAL: Wrong event loop type! Got {loop_type}, need ProactorEventLoop")
            logger.error("❌ Subprocess operations will FAIL! Please restart server.")
        else:
            logger.info("✅ Correct event loop for Windows subprocess support")
    
    await init_app_db()
    
    # Initialize web search client
    web_search_client = WebSearchClient()
    await web_search_client.connect()
    logger.info("🌐 Web search client initialized")



@app.get("/", response_class=FileResponse)
async def root():
    """Serve the main HTML interface"""
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {"message": "MCP Client API (Fixed)", "status": "running"}


@app.get("/api")
async def api_root(request: Request):
    """API root endpoint"""
    return {
        "message": "MCP Client API (Fixed)",
        "status": "running",
        "connected": bool(user_clients.get(request.session.get("username")))
    }

# ------------------ AUTH ------------------
@app.post("/api/auth/signup")
async def signup(req: AuthRequest, request: Request):
    import aiosqlite
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password required")
    try:
        async with aiosqlite.connect(APP_DB_PATH) as db:
            await db.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (req.username, hash_password(req.password), datetime.utcnow().isoformat() + "Z"),
            )
            await db.commit()
    except Exception as e:
        # Likely unique constraint
        raise HTTPException(status_code=400, detail="Username already exists")
    # start session
    request.session["username"] = req.username
    request.session["session_id"] = str(uuid.uuid4())
    return {"status": "signed_up", "username": req.username}

@app.post("/api/auth/signin")
async def signin(req: AuthRequest, request: Request):
    import aiosqlite
    async with aiosqlite.connect(APP_DB_PATH) as db:
        async with db.execute("SELECT password_hash FROM users WHERE username = ?", (req.username,)) as cur:
            row = await cur.fetchone()
            if not row or row[0] != hash_password(req.password):
                raise HTTPException(status_code=401, detail="Invalid credentials")
    request.session["username"] = req.username
    request.session["session_id"] = str(uuid.uuid4())
    return {"status": "signed_in", "username": req.username}

@app.post("/api/auth/signout")
async def signout(request: Request):
    request.session.clear()
    return {"status": "signed_out"}

@app.get("/api/auth/me")
async def me(request: Request):
    return {"username": request.session.get("username")}


@app.get("/api/servers")
async def list_servers():
    """List available MCP servers"""
    servers = MCPServerConfig.get_configs()
    return {
        "servers": list(servers.keys()),
        "count": len(servers)
    }


@app.get("/api/models")
async def list_models():
    """List available OpenRouter models"""
    models = MCPServerConfig.get_available_models()
    return {
        "models": models,
        "count": len(models)
    }


@app.post("/api/connect")
async def connect_to_server(request: ConnectRequest, http_request: Request):
    """Connect to an MCP server"""
    username = get_user_or_anonymous(http_request)
    lock = get_lock_for_user(username)
    async with lock:
        try:
            # Close existing client if any
            if user_clients.get(username):
                logger.info("Closing existing client")
                try:
                    await user_clients[username].close()
                except:
                    pass
                user_clients.pop(username, None)
                user_agents.pop(username, None)
                user_stream_agents.pop(username, None)
            
            # Get server configuration
            server_configs = MCPServerConfig.get_configs()
            if request.server_name not in server_configs:
                raise HTTPException(status_code=404, detail=f"Server '{request.server_name}' not found")
            
            # Create new client
            logger.info(f"Creating client for server: {request.server_name}")
            server_config = server_configs[request.server_name]
            
            # IMPORTANT: For SQLite server, use the currently selected database instead of example.db
            if request.server_name == "SQLite":
                active_database_id = http_request.session.get("active_database_id")
                if active_database_id:
                    # User has selected a database - use that instead of example.db
                    pipeline = get_pipeline(username)
                    try:
                        db_metadata = pipeline.get_database_by_id(active_database_id)
                        db_path = db_metadata["db_path"]
                        
                        # Override server config to use the selected database
                        current_dir = Path(__file__).parent.resolve()
                        sqlite_server_script = str(current_dir / "sqlite_mcp_fastmcp.py")
                        
                        server_config = StdioServerParameters(
                            command=sys.executable,
                            args=["-u", sqlite_server_script, str(Path(db_path).resolve())],
                            env=os.environ.copy(),
                        )
                        logger.info(f"Using selected database: {db_metadata['name']} ({db_path})")
                    except Exception as e:
                        logger.warning(f"Could not load selected database, using default: {e}")
                        # Fall back to default config
            
            client = MCPClient(server_config)
            
            # Connect
            await client.connect()
            
            # Get available tools (full objects)
            tools = await client.list_tools()
            
            # Create LLM agents (regular and streaming) - Always use DEFAULT_MODEL from config
            agent = LLMAgent(client, model=DEFAULT_MODEL)
            streaming_agent = StreamingLLMAgent(client, model=DEFAULT_MODEL)
            
            # Store client and agents for this user
            user_clients[username] = client
            user_agents[username] = agent
            user_stream_agents[username] = streaming_agent
            
            logger.info(f"Successfully connected to {request.server_name} with LLM model {DEFAULT_MODEL}")
            
            # Serialize tools for UI
            tools_json = [
                {
                    "name": getattr(t, "name", ""),
                    "description": getattr(t, "description", "") or ""
                }
                for t in tools
            ]
            
            return {
                "status": "connected",
                "server": request.server_name,
                "model": DEFAULT_MODEL,
                "tools": tools_json,
                "tool_count": len(tools)
            }
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")


@app.post("/api/disconnect")
async def disconnect_from_server(http_request: Request):
    """Disconnect from MCP server"""
    username = get_user_or_anonymous(http_request)
    lock = get_lock_for_user(username)
    async with lock:
        if user_clients.get(username) is None:
            return {"status": "not_connected", "message": "No active connection"}
        
        try:
            await user_clients[username].close()
            user_clients.pop(username, None)
            user_agents.pop(username, None)
            user_stream_agents.pop(username, None)
            return {"status": "disconnected", "message": "Successfully disconnected"}
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            user_clients.pop(username, None)
            user_agents.pop(username, None)
            user_stream_agents.pop(username, None)
            return {"status": "disconnected", "message": f"Disconnected with errors: {str(e)}"}


@app.get("/api/status")
async def get_status(http_request: Request):
    """Get connection status"""
    username = http_request.session.get("username")
    if not username or user_clients.get(username) is None:
        return {
            "connected": False,
            "server": None,
            "model": None,
            "tools": [],
            "conversation_length": 0
        }
    
    try:
        tools_json = []
        
        # Add SQLite tools if connected
        if user_clients.get(username):
            sqlite_tools = await user_clients[username].list_tools()
            for t in sqlite_tools:
                tools_json.append({
                    "name": getattr(t, "name", ""),
                    "description": getattr(t, "description", "") or "",
                    "source": "SQLite"
                })
        
        # Add Notion tools if connected
        if username in user_notion_clients:
            for workspace_id, notion_client in user_notion_clients[username].items():
                if hasattr(notion_client, 'tools'):
                    for tool in notion_client.tools:
                        tools_json.append({
                            "name": tool.get("name", ""),
                            "description": tool.get("description", ""),
                            "source": f"Notion_{workspace_id}"
                        })
        
        # Add Web Search tools (always available)
        if web_search_client and hasattr(web_search_client, 'tools'):
            for tool in web_search_client.tools:
                tools_json.append({
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "source": "WebSearch"
                })
        
        return {
            "connected": True,
            "server": "multi-server" if len(tools_json) > 0 else "none",
            "model": "N/A",
            "tools": tools_json,
            "conversation_length": 0,
            "tool_calls_made": 0
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {
            "connected": False,
            "error": str(e)
        }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request):
    """Send a chat message with intelligent LLM tool calling"""
    username = get_user_or_anonymous(http_request)
    
    # Check if we have any MCP servers (SQLite, Notion, or Web Search)
    has_sqlite = user_clients.get(username) is not None
    has_notion = username in user_notion_clients and len(user_notion_clients[username]) > 0
    has_websearch = web_search_client is not None
    
    if not (has_sqlite or has_notion or has_websearch):
        raise HTTPException(status_code=400, detail="Not connected to MCP server. Connect first.")
    
    try:
        logger.info(f"Processing chat message: {request.message}")
        
        # Use LLM agent for intelligent response
        session_id = http_request.session.get("session_id") or str(uuid.uuid4())
        http_request.session["session_id"] = session_id
        
        # Use multi-server agent if Notion or WebSearch are available
        if has_notion or has_websearch:
            logger.info("🔀 Using multi-server agent (Notion/WebSearch detected)")
            
            # Create multi-server agent
            from llm_multi_server import MultiServerLLMAgent
            agent = MultiServerLLMAgent(model=DEFAULT_MODEL)
            
            # Register clients
            if has_sqlite and user_clients.get(username):
                agent.register_mcp_client("SQLite", user_clients[username])
            
            if has_notion:
                for workspace_id, notion_client in user_notion_clients[username].items():
                    agent.register_mcp_client(f"Notion_{workspace_id}", notion_client)
            
            if has_websearch:
                agent.register_mcp_client("WebSearch", web_search_client)
            
            # Hydrate history
            await hydrate_agent_if_empty(username, session_id, agent)
            
            response_text, tool_calls = await agent.chat(request.message)
        else:
            # Use regular agent (SQLite only)
            await hydrate_agent_if_empty(username, session_id, user_agents[username])
            response_text, tool_calls = await user_agents[username].chat(request.message)
        
        # Convert tool calls to response format
        tool_calls_list = [
            {
                "tool_name": tc.tool_name,
                "arguments": tc.arguments,
                "result": tc.result,
                "duration_ms": tc.duration_ms
            }
            for tc in tool_calls
        ]
        
        logger.info(f"LLM response generated with {len(tool_calls)} tool calls")
        
        # Persist chat both user and assistant turns
        import aiosqlite, json as pyjson
        # session_id already ensured above
        async with aiosqlite.connect(APP_DB_PATH) as db:
            now = datetime.utcnow().isoformat() + "Z"
            await db.execute(
                "INSERT INTO messages (username, session_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (username, session_id, "user", request.message, None, now),
            )
            await db.execute(
                "INSERT INTO messages (username, session_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (username, session_id, "assistant", response_text, pyjson.dumps(tool_calls_list), now),
            )
            await db.commit()
        
        return ChatResponse(
            response=response_text,
            tool_calls=tool_calls_list,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.get("/api/chat/stream")
async def chat_stream(message: str, http_request: Request):
    """Stream chat responses with Server-Sent Events (SSE)
    
    Automatically includes Notion and Web Search tools when available.
    """
    username = get_user_or_anonymous(http_request)
    
    # Check if we have any MCP servers (SQLite, Notion, or Web Search)
    has_sqlite = user_clients.get(username) is not None
    has_notion = username in user_notion_clients and len(user_notion_clients[username]) > 0
    has_websearch = web_search_client is not None
    
    if not (has_sqlite or has_notion or has_websearch):
        raise HTTPException(status_code=400, detail="No MCP servers connected. Connect to SQLite, Notion, or use Web Search.")
    
    async def event_generator():
        """Generate SSE events from LLM stream"""
        try:
            logger.info(f"Starting streaming chat: {message}")
            # Persist the user message immediately
            import aiosqlite, json as pyjson
            session_id = http_request.session.get("session_id") or str(uuid.uuid4())
            http_request.session["session_id"] = session_id
            async with aiosqlite.connect(APP_DB_PATH) as db:
                await db.execute(
                    "INSERT INTO messages (username, session_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (username, session_id, "user", message, None, datetime.utcnow().isoformat() + "Z"),
                )
                await db.commit()

            assistant_buffer = ""
            reasoning_buffer = ""
            tool_calls_accum: list[dict[str, Any]] = []

            # Use multi-server agent if Notion or WebSearch are available
            if has_notion or (has_websearch and not has_sqlite):
                # Use streaming multi-server agent
                logger.info("🔀 Using streaming multi-server agent (Notion/WebSearch detected)")
                
                # Create streaming multi-server agent
                from llm_multi_server_streaming import StreamingMultiServerLLMAgent
                agent = StreamingMultiServerLLMAgent(model=DEFAULT_MODEL)
                
                # Register clients
                if has_sqlite and user_clients.get(username):
                    agent.register_mcp_client("SQLite", user_clients[username])
                
                if has_notion:
                    for workspace_id, notion_client in user_notion_clients[username].items():
                        agent.register_mcp_client(f"Notion_{workspace_id}", notion_client)
                
                if has_websearch:
                    agent.register_mcp_client("WebSearch", web_search_client)
                
                # Hydrate history
                await hydrate_agent_if_empty(username, session_id, agent)
                
                # Stream response with proper events
                async for event in agent.chat_stream(message):
                    # Convert event to SSE format
                    event_data = json.dumps(event)
                    yield f"data: {event_data}\n\n"
                    
                    # Accumulate for storage
                    etype = event.get("type")
                    if etype == "text_chunk":
                        assistant_buffer += event.get("content", "")
                    elif etype == "reasoning_chunk":
                        reasoning_buffer += event.get("content", "")
                    elif etype == "tool_result":
                        tool_calls_accum.append({"tool_name": event.get("tool_name"), "result": event.get("result")})
            else:
                # Use regular streaming agent (SQLite only)
                await hydrate_agent_if_empty(username, session_id, user_stream_agents[username])
                async for event in user_stream_agents[username].chat_stream(message):
                    # Convert event to SSE format
                    event_data = json.dumps(event)
                    yield f"data: {event_data}\n\n"

                    # Accumulate for storage
                    etype = event.get("type")
                    if etype == "text_chunk":
                        assistant_buffer += event.get("content", "")
                    elif etype == "reasoning_chunk":
                        reasoning_buffer += event.get("content", "")
                    elif etype == "tool_result":
                        tool_calls_accum.append({"tool_name": event.get("tool_name"), "result": event.get("result")})
            
            logger.info("Streaming chat completed")
            # Persist assistant turn
            try:
                async with aiosqlite.connect(APP_DB_PATH) as db:
                    meta = json.dumps({"tool_calls": tool_calls_accum, "reasoning": reasoning_buffer})
                    await db.execute(
                        "INSERT INTO messages (username, session_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (username, http_request.session.get("session_id"), "assistant", assistant_buffer or "", meta, datetime.utcnow().isoformat() + "Z"),
                    )
                    await db.commit()
            except Exception as e:
                logger.warning(f"Failed to persist assistant message: {e}")
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            error_event = json.dumps({
                "type": "error",
                "error": str(e)
            })
            yield f"data: {error_event}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/chat/multi")
async def chat_multi_server(request: ChatRequest, http_request: Request):
    """Chat with access to multiple MCP servers (SQLite + Notion)
    
    This endpoint allows users to query both SQLite databases and Notion workspaces
    in a single conversation. The LLM will automatically route tool calls to the
    appropriate server based on the user's request.
    """
    username = get_user_or_anonymous(http_request)
    session_id = http_request.session.get("session_id") or str(uuid.uuid4())
    http_request.session["session_id"] = session_id
    
    try:
        logger.info(f"🔀 Multi-server chat: {request.message}")
        
        # Create multi-server agent
        agent = MultiServerLLMAgent(model=DEFAULT_MODEL)
        
        # Register SQLite client if connected
        sqlite_client = user_clients.get(username)
        if sqlite_client:
            agent.register_mcp_client("SQLite", sqlite_client)
            logger.info("✅ Registered SQLite MCP")
        
        # Register Notion clients if connected
        if username in user_notion_clients:
            for workspace_id, notion_client in user_notion_clients[username].items():
                agent.register_mcp_client(f"Notion_{workspace_id}", notion_client)
                logger.info(f"✅ Registered Notion MCP: {workspace_id}")
        
        # Register web search client (always available)
        if web_search_client:
            agent.register_mcp_client("WebSearch", web_search_client)
            logger.info("✅ Registered Web Search MCP")
        
        # Check if any servers are connected
        if not agent.mcp_clients:
            raise HTTPException(
                status_code=400,
                detail="No MCP servers connected. Please connect to SQLite or Notion first."
            )
        
        # Hydrate conversation history from database
        await hydrate_agent_if_empty(username, session_id, agent)
        
        # Process message
        response = await agent.chat(request.message)
        
        # Save messages to database
        import aiosqlite
        now = datetime.utcnow().isoformat() + "Z"
        async with aiosqlite.connect(APP_DB_PATH) as db:
            # Save user message
            await db.execute(
                "INSERT INTO messages (username, session_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (username, session_id, "user", request.message, None, now),
            )
            # Save assistant message
            metadata = json.dumps({
                "tool_calls": response.get("tool_calls", []),
                "servers_used": response.get("servers_used", [])
            })
            await db.execute(
                "INSERT INTO messages (username, session_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (username, session_id, "assistant", response["content"], metadata, now),
            )
            await db.commit()
        
        logger.info(f"✅ Multi-server chat completed. Servers used: {response.get('servers_used', [])}")
        
        return {
            "response": response["content"],
            "tool_calls": response.get("tool_calls", []),
            "servers_used": response.get("servers_used", []),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Multi-server chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.post("/api/clear")
async def clear_conversation(http_request: Request):
    """Clear conversation history"""
    username = get_user_or_anonymous(http_request)
    if user_agents.get(username):
        user_agents[username].clear_history()
    if user_stream_agents.get(username):
        user_stream_agents[username].clear_history()
    # Clear stored messages for current session id
    import aiosqlite
    session_id = http_request.session.get("session_id")
    if session_id:
        async with aiosqlite.connect(APP_DB_PATH) as db:
            await db.execute("DELETE FROM messages WHERE username = ? AND session_id = ?", (username, session_id))
            await db.commit()
    return {"status": "cleared", "message": "Conversation history cleared"}


@app.get("/api/history")
async def get_history(http_request: Request, limit: int = 50):
    """Return recent chat history for the current session (ascending order)."""
    username = get_user_or_anonymous(http_request)
    session_id = http_request.session.get("session_id")
    if not session_id:
        return {"messages": []}
    try:
        import aiosqlite
        rows = []
        async with aiosqlite.connect(APP_DB_PATH) as db:
            async with db.execute(
                "SELECT role, content, created_at FROM messages WHERE username = ? AND session_id = ? ORDER BY id DESC LIMIT ?",
                (username, session_id, limit),
            ) as cur:
                rows = await cur.fetchall()
        # return chronological
        messages = [{"role": r[0], "content": r[1] or "", "created_at": r[2]} for r in reversed(rows)]
        return {"messages": messages}
    except Exception as e:
        logger.error(f"History fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to load history")


# ===================== FILE UPLOAD & DATABASE MANAGEMENT ENDPOINTS =====================

@app.post("/api/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Upload and convert CSV/Excel file to SQLite"""
    username = get_user_or_anonymous(request)
    
    # Validate file type
    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}. Only CSV, XLSX, and XLS are supported.")
    
    # Validate file size (100MB max)
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    
    max_size = 100 * 1024 * 1024  # 100MB
    if size > max_size:
        raise HTTPException(status_code=400, detail=f"File too large ({size} bytes). Maximum size is 100MB.")
    
    temp_path = None
    try:
        # Resolve per-user pipeline and ensure directories exist
        pipeline = get_pipeline(username)
        # Save uploaded file temporarily
        temp_path = pipeline.original_dir / f"temp_{uuid.uuid4()}{file_ext}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File uploaded: {file.filename} ({size} bytes)")
        
        # Process file
        result = await pipeline.process_upload(temp_path, file.filename)
        
        # Move to permanent location
        final_path = pipeline.original_dir / f"{result['database_id']}{file_ext}"
        temp_path.rename(final_path)
        
        logger.info(f"File converted successfully: {result['database_id']}")
        
        # AUTO-CONNECT: Automatically switch to and connect to the newly uploaded database
        database_id = result['database_id']
        db_path = result.get('db_path') or (pipeline.db_dir / f"{database_id}.db")
        
        logger.info(f"✅ Auto-connecting to uploaded database: {database_id}")
        
        lock = get_lock_for_user(username)
        async with lock:
            # Disconnect current client if any
            if user_clients.get(username):
                try:
                    await user_clients[username].close()
                except Exception as e:
                    logger.warning(f"Error closing previous client: {e}")
            
            # Create new server config for uploaded database
            current_dir = Path(__file__).parent.resolve()
            sqlite_server_script = str(current_dir / "sqlite_mcp_fastmcp.py")
            
            server_config = StdioServerParameters(
                command=sys.executable,
                args=["-u", sqlite_server_script, str(Path(db_path).resolve())],
                env=os.environ.copy(),
            )
            
            # Connect to new database
            client = MCPClient(server_config)
            await client.connect()
            
            # Create agents
            agent = LLMAgent(client, model=DEFAULT_MODEL)
            streaming_agent = StreamingLLMAgent(client, model=DEFAULT_MODEL)
            
            user_clients[username] = client
            user_agents[username] = agent
            user_stream_agents[username] = streaming_agent
            
            # Update session
            pipeline.update_active_database(database_id)
            new_session_id = f"db_{database_id}"
            request.session["session_id"] = new_session_id
            request.session["active_database_id"] = database_id
            
            logger.info(f"✅ Auto-connected to uploaded database successfully")
        
        return {
            "status": "success",
            "message": "File uploaded, converted, and connected successfully",
            "connected": True,  # Signal to frontend that connection is active
            **result
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        if temp_path and temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/databases")
async def list_databases(request: Request):
    """List all uploaded databases"""
    try:
        username = get_user_or_anonymous(request)
        pipeline = get_pipeline(username)
        result = pipeline.list_databases()
        
        # Include active database ID from session
        result["active_database_id"] = request.session.get("active_database_id")
        result["session_id"] = request.session.get("session_id")
        
        return result
    except Exception as e:
        logger.error(f"Failed to list databases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/switch-database")
async def switch_database(request: dict, http_request: Request):
    """Switch to a different uploaded database"""
    username = get_user_or_anonymous(http_request)
    database_id = request.get("database_id")
    if not database_id:
        raise HTTPException(status_code=400, detail="database_id is required")
    
    try:
        pipeline = get_pipeline(username)
        
        try:
            db_metadata = pipeline.get_database_by_id(database_id)
        except ValueError as e:
            # Database not found for current user, try to find it across all users
            logger.warning(f"Database {database_id} not found for user {username}, searching all users")
            
            # Search through all user directories
            uploads_dir = Path("uploads")
            if not uploads_dir.exists():
                raise HTTPException(status_code=404, detail="Database not found")
            
            found_metadata = None
            for user_dir in uploads_dir.iterdir():
                if user_dir.is_dir() and user_dir.name != "databases" and user_dir.name != "original_files":
                    user_pipeline = DataPipeline(upload_dir=str(user_dir))
                    try:
                        user_metadata = user_pipeline.get_database_by_id(database_id)
                        found_metadata = user_metadata
                        logger.info(f"Found database {database_id} in user directory: {user_dir.name}")
                        break
                    except ValueError:
                        continue
            
            if not found_metadata:
                raise HTTPException(status_code=404, detail="Database not found")
            
            db_metadata = found_metadata
        db_path = db_metadata["db_path"]
        
        logger.info(f"Switching to database: {db_metadata['name']} ({db_path})")
        
        lock = get_lock_for_user(username)
        async with lock:
            # Disconnect current client
            if user_clients.get(username):
                try:
                    await user_clients[username].close()
                except Exception as e:
                    logger.warning(f"Error closing previous client: {e}")
            
            # Create new server config for this database
            # Use absolute paths for production deployment
            current_dir = Path(__file__).parent.resolve()
            sqlite_server_script = str(current_dir / "sqlite_mcp_fastmcp.py")
            
            server_config = StdioServerParameters(
                command=sys.executable,
                args=["-u", sqlite_server_script, str(Path(db_path).resolve())],
                env=os.environ.copy(),
            )
            
            # Connect to new database
            client = MCPClient(server_config)
            await client.connect()
            
            # Always use DEFAULT_MODEL from config (modular approach)
            # Create new agents
            agent = LLMAgent(client, model=DEFAULT_MODEL)
            streaming_agent = StreamingLLMAgent(client, model=DEFAULT_MODEL)
            
            user_clients[username] = client
            user_agents[username] = agent
            user_stream_agents[username] = streaming_agent
            
            # Update metadata
            pipeline.update_active_database(database_id)
            
            # IMPORTANT: Use deterministic session ID to preserve chat history per database
            # Format: "db_{database_id}" - This allows returning to same conversation
            # when switching back to the same database
            new_session_id = f"db_{database_id}"
            http_request.session["session_id"] = new_session_id
            http_request.session["active_database_id"] = database_id
            
            logger.info(f"Successfully switched to database: {db_metadata['name']}")
            logger.info(f"Restored session: {new_session_id}")
            
            return {
                "status": "success",
                "connected": True,  # Signal to frontend that connection is active
                "database_name": db_metadata["name"],
                "database_id": database_id,
                "tables": db_metadata.get("tables", [])
            }
            
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        import traceback
        logger.error(f"Database switch failed: {type(e).__name__}: {str(e)}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        logger.error(f"Database path attempted: {db_path if 'db_path' in locals() else 'N/A'}")
        logger.error(f"Server script: {sqlite_server_script if 'sqlite_server_script' in locals() else 'N/A'}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/database/{database_id}/info")
async def get_database_info(database_id: str, request: Request):
    """Get detailed database information"""
    try:
        username = get_user_or_anonymous(request)
        logger.info(f"Getting database info for {database_id} for user {username}")
        
        pipeline = get_pipeline(username)
        
        try:
            db_metadata = pipeline.get_database_by_id(database_id)
            logger.info(f"Found database {database_id} in user {username}'s directory")
        except ValueError as e:
            # Database not found for current user, try to find it across all users
            logger.warning(f"Database {database_id} not found for user {username}, searching all users: {e}")
            
            # Search through all user directories
            uploads_dir = Path("uploads")
            if not uploads_dir.exists():
                logger.error(f"Uploads directory does not exist: {uploads_dir}")
                raise HTTPException(status_code=404, detail="Database not found")
            
            found_metadata = None
            try:
                for user_dir in uploads_dir.iterdir():
                    if user_dir.is_dir() and user_dir.name not in ["databases", "original_files"]:
                        logger.info(f"Searching in user directory: {user_dir.name}")
                        try:
                            user_pipeline = DataPipeline(upload_dir=str(user_dir))
                            user_metadata = user_pipeline.get_database_by_id(database_id)
                            found_metadata = user_metadata
                            logger.info(f"Found database {database_id} in user directory: {user_dir.name}")
                            break
                        except ValueError as ve:
                            logger.debug(f"Database {database_id} not found in {user_dir.name}: {ve}")
                            continue
                        except Exception as ue:
                            logger.error(f"Error searching in {user_dir.name}: {ue}")
                            continue
            except Exception as se:
                logger.error(f"Error during cross-user search: {se}")
                raise HTTPException(status_code=500, detail=f"Search error: {str(se)}")
            
            if not found_metadata:
                logger.warning(f"Database {database_id} not found in any user directory")
                raise HTTPException(status_code=404, detail="Database not found")
            
            db_metadata = found_metadata
        
        db_path = Path(db_metadata["db_path"])
        
        if not db_path.exists():
            raise HTTPException(status_code=404, detail="Database file not found")
        
        # Get table details from SQLite
        import aiosqlite
        
        tables_info = []
        try:
            async with aiosqlite.connect(db_path) as db:
                for table_meta in db_metadata.get("tables", []):
                    table_name = table_meta["name"]
                    logger.info(f"Getting info for table: {table_name}")
                    
                    try:
                        # Get column info
                        cursor = await db.execute(f"PRAGMA table_info({table_name})")
                        columns_raw = await cursor.fetchall()
                        
                        columns = [
                            {
                                "name": col[1],
                                "type": col[2],
                                "nullable": not bool(col[3]),
                                "primary_key": bool(col[5])
                            }
                            for col in columns_raw
                        ]
                        
                        # Get row count
                        cursor = await db.execute(f"SELECT COUNT(*) FROM {table_name}")
                        row_count = (await cursor.fetchone())[0]
                        
                        tables_info.append({
                            "name": table_name,
                            "row_count": row_count,
                            "columns": columns
                        })
                        
                        logger.info(f"Successfully processed table {table_name}: {row_count} rows, {len(columns)} columns")
                    except Exception as te:
                        logger.error(f"Error processing table {table_name}: {te}")
                        # Continue with other tables even if one fails
                        continue
        except Exception as db_error:
            logger.error(f"Error connecting to database {db_path}: {db_error}")
            raise HTTPException(status_code=500, detail=f"Database connection error: {str(db_error)}")
        
        logger.info(f"Successfully retrieved info for database {database_id}: {len(tables_info)} tables")
        
        return {
            "id": database_id,
            "name": db_metadata["name"],
            "tables": tables_info,
            "size_bytes": db_metadata.get("size_bytes", 0),
            "uploaded_at": db_metadata.get("uploaded_at", "")
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/database/{database_id}")
async def delete_database(database_id: str, request: Request):
    """Delete an uploaded database"""
    try:
        pipeline = get_pipeline(get_user_or_anonymous(request))
        db_metadata = pipeline.get_database_by_id(database_id)
        
        # If this is the active database, disconnect first
        username = request.session.get("username")
        if user_clients.get(username) and db_metadata.get("is_active"):
            lock = get_lock_for_user(username)
            async with lock:
                try:
                    await user_clients[username].close()
                except:
                    pass
                user_clients.pop(username, None)
                user_agents.pop(username, None)
                user_stream_agents.pop(username, None)
        
        # Delete database
        pipeline.delete_database(database_id)
        
        logger.info(f"Database deleted: {database_id}")
        
        return {
            "status": "success",
            "message": f"Database '{db_metadata['name']}' deleted successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete database: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ================ NOTION MCP INTEGRATION ================

async def get_notion_client(username: str, workspace_id: str) -> Optional[NotionAPIClient]:
    """Get or create Notion API client for user workspace"""
    
    # Check if client already exists
    if username in user_notion_clients:
        if workspace_id in user_notion_clients[username]:
            return user_notion_clients[username][workspace_id]
    
    # Fetch token from database
    import aiosqlite
    async with aiosqlite.connect(APP_DB_PATH) as db:
        async with db.execute(
            "SELECT access_token FROM notion_tokens WHERE username = ? AND workspace_id = ?",
            (username, workspace_id)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            access_token = row[0]
    
    # Create and connect client
    client = NotionAPIClient(access_token)
    success = await client.connect()
    
    if success:
        if username not in user_notion_clients:
            user_notion_clients[username] = {}
        user_notion_clients[username][workspace_id] = client
        logger.info(f"✅ Notion API client created for {username}/{workspace_id}")
        return client
    else:
        logger.error(f"❌ Failed to connect Notion API for {username}/{workspace_id}")
        return None


@app.get("/api/notion/auth")
async def notion_auth(request: Request):
    """Initiate Notion OAuth flow"""
    username = get_user_or_anonymous(request)
    
    if not NOTION_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Notion OAuth not configured. Please set NOTION_CLIENT_ID in .env"
        )
    
    # Generate state for CSRF protection
    state = str(uuid.uuid4())
    request.session["notion_oauth_state"] = state
    
    # Build OAuth URL
    from urllib.parse import urlencode
    params = {
        "client_id": NOTION_CLIENT_ID,
        "response_type": "code",
        "owner": "user",
        "redirect_uri": NOTION_REDIRECT_URI,
        "state": state
    }
    
    oauth_url = f"{NOTION_OAUTH_URL}?{urlencode(params)}"
    
    logger.info(f"🔐 Notion OAuth initiated for {username}")
    return {"oauth_url": oauth_url}


@app.get("/api/notion/callback")
async def notion_callback(code: str, state: str, request: Request):
    """Handle Notion OAuth callback"""
    username = get_user_or_anonymous(request)
    
    # Verify state (CSRF protection)
    stored_state = request.session.get("notion_oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        auth_header = httpx.BasicAuth(NOTION_CLIENT_ID, NOTION_CLIENT_SECRET)
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": NOTION_REDIRECT_URI
        }
        headers = {"Notion-Version": NOTION_API_VERSION}
        
        try:
            response = await client.post(
                NOTION_TOKEN_URL,
                auth=auth_header,
                json=data,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"OAuth token exchange failed: {response.text}")
                raise HTTPException(
                    status_code=400,
                    detail=f"OAuth token exchange failed: {response.text}"
                )
            
            token_data = response.json()
            logger.info(f"🔍 OAuth token response keys: {list(token_data.keys())}")
            logger.info(f"🔍 Access token preview: {token_data.get('access_token', 'N/A')[:30]}...")
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Notion API timeout")
        except Exception as e:
            logger.error(f"OAuth exchange error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Store token in database
    import aiosqlite
    async with aiosqlite.connect(APP_DB_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO notion_tokens 
            (username, access_token, workspace_id, workspace_name, workspace_icon, bot_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                token_data["access_token"],
                token_data.get("workspace_id", ""),
                token_data.get("workspace_name", ""),
                token_data.get("workspace_icon", ""),
                token_data.get("bot_id", ""),
                datetime.utcnow().isoformat() + "Z"
            )
        )
        await db.commit()
    
    logger.info(f"✅ Notion OAuth completed for {username} - Workspace: {token_data.get('workspace_name')}")
    
    # Return HTML that closes the popup and notifies parent window
    from fastapi.responses import HTMLResponse
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Notion Connected</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }}
            .container {{
                text-align: center;
                padding: 40px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                backdrop-filter: blur(10px);
            }}
            .checkmark {{
                font-size: 64px;
                margin-bottom: 20px;
            }}
            h1 {{
                margin: 0 0 10px 0;
                font-size: 28px;
            }}
            p {{
                margin: 0;
                font-size: 16px;
                opacity: 0.9;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="checkmark">✅</div>
            <h1>Notion Connected!</h1>
            <p>Workspace: {token_data.get('workspace_name', 'Unknown')}</p>
            <p style="margin-top: 20px; font-size: 14px;">This window will close automatically...</p>
        </div>
        <script>
            // Notify opener window and close
            if (window.opener) {{
                window.opener.postMessage({{type: 'notion_oauth_success'}}, '*');
            }}
            setTimeout(() => {{
                window.close();
            }}, 2000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/notion/workspaces")
async def list_notion_workspaces(request: Request):
    """List user's connected Notion workspaces"""
    username = get_user_or_anonymous(request)
    
    # Check if Notion is configured
    if not NOTION_CLIENT_ID:
        logger.warning("Notion OAuth not configured - returning empty workspaces")
        return {"workspaces": []}
    
    import aiosqlite
    workspaces = []
    async with aiosqlite.connect(APP_DB_PATH) as db:
        async with db.execute(
            "SELECT workspace_id, workspace_name, workspace_icon FROM notion_tokens WHERE username = ?",
            (username,)
        ) as cur:
            async for row in cur:
                workspaces.append({
                    "workspace_id": row[0],
                    "workspace_name": row[1],
                    "workspace_icon": row[2]
                })
    
    logger.info(f"📋 Listed {len(workspaces)} Notion workspaces for {username}")
    return {"workspaces": workspaces}


@app.post("/api/notion/connect")
async def connect_notion_mcp(workspace_id: str, request: Request):
    """Connect to Notion MCP for a specific workspace"""
    username = get_user_or_anonymous(request)
    
    # Check if Notion is configured
    if not NOTION_CLIENT_ID:
        raise HTTPException(
            status_code=503, 
            detail="Notion OAuth not configured. Please set NOTION_CLIENT_ID in .env"
        )
    
    client = await get_notion_client(username, workspace_id)
    if not client:
        raise HTTPException(status_code=400, detail="Failed to connect to Notion")
    
    return {
        "status": "connected",
        "workspace_id": workspace_id,
        "tools": client.tools,
        "tool_count": len(client.tools)
    }


@app.delete("/api/notion/disconnect/{workspace_id}")
async def disconnect_notion(workspace_id: str, request: Request):
    """Disconnect Notion workspace"""
    username = get_user_or_anonymous(request)
    
    # Close client if exists
    if username in user_notion_clients:
        if workspace_id in user_notion_clients[username]:
            try:
                await user_notion_clients[username][workspace_id].close()
            except:
                pass
            del user_notion_clients[username][workspace_id]
    
    # Remove from database
    import aiosqlite
    async with aiosqlite.connect(APP_DB_PATH) as db:
        await db.execute(
            "DELETE FROM notion_tokens WHERE username = ? AND workspace_id = ?",
            (username, workspace_id)
        )
        await db.commit()
    
    logger.info(f"🔌 Disconnected Notion workspace {workspace_id} for {username}")
    return {"status": "disconnected"}


# ================ SHUTDOWN ================

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    # Close all SQLite MCP clients
    for username, client in list(user_clients.items()):
        logger.info(f"Shutting down - closing MCP client for {username}")
        try:
            await client.close()
        except Exception as e:
            logger.error(f"Error during shutdown for {username}: {e}")
    user_clients.clear()
    user_agents.clear()
    user_stream_agents.clear()
    
    # Close all Notion MCP clients
    for username, workspaces in list(user_notion_clients.items()):
        for workspace_id, client in workspaces.items():
            logger.info(f"Shutting down - closing Notion MCP for {username}/{workspace_id}")
            try:
                await client.close()
            except Exception as e:
                logger.error(f"Error closing Notion client: {e}")
    user_notion_clients.clear()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
