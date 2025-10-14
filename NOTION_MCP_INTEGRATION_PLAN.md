# 🚀 Notion MCP Integration Plan
## Dynamic User Inputs from Frontend

---

## 📋 **Overview**

This document outlines a comprehensive plan to integrate **Notion MCP** into your existing **MCP Database Assistant** project, enabling users to:

1. **Authenticate with Notion** via OAuth
2. **Connect to Notion workspaces** dynamically
3. **Query Notion databases and pages** with natural language
4. **Manage multiple MCP servers** (SQLite + Notion) simultaneously
5. **Provide dynamic user inputs** from the frontend for Notion operations

---

## 🏗️ **Architecture Overview**

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (HTML/JS)                       │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ SQLite UI  │  │  Notion UI   │  │  Chat Interface  │  │
│  │ (Existing) │  │    (NEW)     │  │   (Enhanced)     │  │
│  └────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (Python)                       │
│  ┌────────────────┐  ┌───────────────────────────────┐   │
│  │ User Auth      │  │  Session Management           │   │
│  │ (Existing)     │  │  (SQLite + Cookies)           │   │
│  └────────────────┘  └───────────────────────────────┘   │
│                                                             │
│  ┌────────────────┐  ┌───────────────────────────────┐   │
│  │ SQLite MCP     │  │  Notion MCP (NEW)             │   │
│  │ Client         │  │  - OAuth Handler              │   │
│  │ (Existing)     │  │  - Token Storage              │   │
│  │                │  │  - Remote MCP Connection      │   │
│  └────────────────┘  └───────────────────────────────┘   │
│                                                             │
│  ┌───────────────────────────────────────────────────┐   │
│  │        LLM Agent (OpenRouter)                     │   │
│  │  - Multi-server tool routing                      │   │
│  │  - Context management                             │   │
│  │  - Streaming responses                            │   │
│  └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              External MCP Servers                           │
│  ┌────────────────┐         ┌──────────────────────┐      │
│  │ SQLite MCP     │         │  Notion Remote MCP   │      │
│  │ (Local)        │         │  https://mcp.notion.com│    │
│  │ - DB queries   │         │  - OAuth protected    │      │
│  │ - Schema ops   │         │  - Databases          │      │
│  └────────────────┘         │  - Pages              │      │
│                              │  - Comments           │      │
│                              └──────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 **Key Features to Implement**

### 1. **Notion OAuth Authentication**
   - OAuth 2.0 flow implementation
   - Token storage per user
   - Token refresh mechanism
   - Workspace information display

### 2. **Remote MCP Connection**
   - Connect to `https://mcp.notion.com/mcp` (Streamable HTTP)
   - Pass OAuth tokens for authentication
   - Handle remote tool discovery

### 3. **Multi-Server Management**
   - Support multiple MCP servers per user (SQLite + Notion)
   - Route tool calls to correct server
   - Unified chat interface

### 4. **Dynamic User Inputs**
   - Frontend forms for database selection
   - Page ID input fields
   - Search query builders
   - Database query filters

### 5. **Notion-Specific Tools**
   - List databases
   - Query database entries
   - Create/update pages
   - Search workspace
   - Add comments

---

## 📝 **Implementation Steps**

### **Phase 1: Backend OAuth & Token Management**

#### **Step 1.1: Create Notion OAuth Configuration**

**File:** `config.py` (update)

```python
# Notion OAuth Settings
NOTION_CLIENT_ID = os.getenv("NOTION_CLIENT_ID")
NOTION_CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET")
NOTION_REDIRECT_URI = os.getenv("NOTION_REDIRECT_URI", "http://localhost:8000/api/notion/callback")
NOTION_OAUTH_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"
NOTION_MCP_URL = "https://mcp.notion.com/mcp"
```

**Environment Variables (`.env`):**

```env
# Existing
OPENROUTER_API_KEY=your-openrouter-key
DEFAULT_MODEL=z-ai/glm-4.5-air:free

# NEW: Notion OAuth
NOTION_CLIENT_ID=your-notion-oauth-client-id
NOTION_CLIENT_SECRET=your-notion-oauth-client-secret
NOTION_REDIRECT_URI=http://localhost:8000/api/notion/callback
```

---

#### **Step 1.2: Database Schema for Notion Tokens**

**File:** `fastapi_app_fixed.py` (update `init_app_db()`)

```python
async def init_app_db():
    import aiosqlite
    async with aiosqlite.connect(APP_DB_PATH) as db:
        # Existing tables (users, messages)
        # ...
        
        # NEW: Notion OAuth tokens table
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
```

---

#### **Step 1.3: Notion OAuth Endpoints**

**File:** `fastapi_app_fixed.py` (add new endpoints)

```python
import httpx
from config import (
    NOTION_CLIENT_ID,
    NOTION_CLIENT_SECRET,
    NOTION_REDIRECT_URI,
    NOTION_OAUTH_URL,
    NOTION_TOKEN_URL
)

# ------------------ NOTION OAUTH ------------------

@app.get("/api/notion/auth")
async def notion_auth(request: Request):
    """Initiate Notion OAuth flow"""
    username = require_user(request)
    
    # Generate state for CSRF protection
    state = str(uuid.uuid4())
    request.session["notion_oauth_state"] = state
    
    # Build OAuth URL
    params = {
        "client_id": NOTION_CLIENT_ID,
        "response_type": "code",
        "owner": "user",
        "redirect_uri": NOTION_REDIRECT_URI,
        "state": state
    }
    
    oauth_url = f"{NOTION_OAUTH_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    
    return {"oauth_url": oauth_url}


@app.get("/api/notion/callback")
async def notion_callback(code: str, state: str, request: Request):
    """Handle Notion OAuth callback"""
    username = require_user(request)
    
    # Verify state (CSRF protection)
    stored_state = request.session.get("notion_oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        auth = (NOTION_CLIENT_ID, NOTION_CLIENT_SECRET)
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": NOTION_REDIRECT_URI
        }
        headers = {"Notion-Version": "2022-06-28"}
        
        response = await client.post(
            NOTION_TOKEN_URL,
            auth=auth,
            json=data,
            headers=headers
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="OAuth token exchange failed")
        
        token_data = response.json()
    
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
    
    # Redirect to chat page with success message
    return FileResponse("static/notion_success.html")  # Or redirect


@app.get("/api/notion/workspaces")
async def list_notion_workspaces(request: Request):
    """List user's connected Notion workspaces"""
    username = require_user(request)
    
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
    
    return {"workspaces": workspaces}


@app.delete("/api/notion/disconnect/{workspace_id}")
async def disconnect_notion(workspace_id: str, request: Request):
    """Disconnect Notion workspace"""
    username = require_user(request)
    
    import aiosqlite
    async with aiosqlite.connect(APP_DB_PATH) as db:
        await db.execute(
            "DELETE FROM notion_tokens WHERE username = ? AND workspace_id = ?",
            (username, workspace_id)
        )
        await db.commit()
    
    return {"status": "disconnected"}
```

---

### **Phase 2: Notion MCP Client Integration**

#### **Step 2.1: Create Notion MCP Client**

**File:** `notion_mcp_client.py` (NEW)

```python
"""
Notion MCP Client - Remote HTTP Connection
Connects to Notion's hosted MCP server with OAuth
"""
import httpx
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class NotionMCPClient:
    """Client for Notion Remote MCP Server"""
    
    def __init__(self, access_token: str, mcp_url: str = "https://mcp.notion.com/mcp"):
        self.access_token = access_token
        self.mcp_url = mcp_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.tools: List[Dict[str, Any]] = []
    
    async def connect(self):
        """Initialize connection and discover tools"""
        try:
            # Tool discovery via MCP protocol
            response = await self.client.post(
                f"{self.mcp_url}/tools/list",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.tools = data.get("tools", [])
                logger.info(f"Connected to Notion MCP. Found {len(self.tools)} tools.")
                return True
            else:
                logger.error(f"Failed to connect: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Notion tool"""
        try:
            response = await self.client.post(
                f"{self.mcp_url}/tools/call",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "name": tool_name,
                    "arguments": arguments
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Tool call failed: {response.status_code}"}
        except Exception as e:
            logger.error(f"Tool call error: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()
```

---

#### **Step 2.2: Integrate Notion Client into FastAPI**

**File:** `fastapi_app_fixed.py` (update)

```python
from notion_mcp_client import NotionMCPClient

# Per-user Notion MCP clients
user_notion_clients: dict[str, Dict[str, NotionMCPClient]] = {}

async def get_notion_client(username: str, workspace_id: str) -> Optional[NotionMCPClient]:
    """Get or create Notion MCP client for user workspace"""
    
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
    client = NotionMCPClient(access_token)
    success = await client.connect()
    
    if success:
        if username not in user_notion_clients:
            user_notion_clients[username] = {}
        user_notion_clients[username][workspace_id] = client
        return client
    else:
        return None


@app.post("/api/notion/connect")
async def connect_notion_mcp(request: Request, workspace_id: str):
    """Connect to Notion MCP for a specific workspace"""
    username = require_user(request)
    
    client = await get_notion_client(username, workspace_id)
    if not client:
        raise HTTPException(status_code=400, detail="Failed to connect to Notion")
    
    return {
        "status": "connected",
        "workspace_id": workspace_id,
        "tools": client.tools
    }
```

---

### **Phase 3: Multi-Server LLM Agent**

#### **Step 3.1: Update LLM Agent to Support Multiple Servers**

**File:** `llm_integration.py` (enhance)

```python
class MultiServerLLMAgent(LLMAgent):
    """LLM Agent supporting multiple MCP servers"""
    
    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key, model)
        self.mcp_clients: Dict[str, Any] = {}  # server_name -> client
        self.tool_routing: Dict[str, str] = {}  # tool_name -> server_name
    
    def register_mcp_client(self, server_name: str, client: Any):
        """Register an MCP client (SQLite, Notion, etc.)"""
        self.mcp_clients[server_name] = client
        
        # Update tool routing
        tools = getattr(client, 'tools', [])
        for tool in tools:
            tool_name = tool.get('name', '')
            self.tool_routing[tool_name] = server_name
            
        logger.info(f"Registered {server_name} with {len(tools)} tools")
    
    async def execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """Route tool call to correct MCP server"""
        server_name = self.tool_routing.get(tool_name)
        
        if not server_name:
            return {"error": f"Unknown tool: {tool_name}"}
        
        client = self.mcp_clients.get(server_name)
        if not client:
            return {"error": f"Server not connected: {server_name}"}
        
        try:
            result = await client.call_tool(tool_name, tool_input)
            return result
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"error": str(e)}
    
    def get_all_tools(self) -> List[Dict]:
        """Get combined tools from all servers"""
        all_tools = []
        for server_name, client in self.mcp_clients.items():
            tools = getattr(client, 'tools', [])
            for tool in tools:
                tool_copy = tool.copy()
                tool_copy['server'] = server_name
                all_tools.append(tool_copy)
        return all_tools
```

---

#### **Step 3.2: Update Chat Endpoint to Use Multi-Server Agent**

**File:** `fastapi_app_fixed.py` (update)

```python
@app.post("/api/chat/multi")
async def chat_multi_server(req: ChatRequest, request: Request):
    """Chat with access to multiple MCP servers (SQLite + Notion)"""
    username = require_user(request)
    session_id = request.session.get("session_id")
    
    # Create multi-server agent
    agent = MultiServerLLMAgent(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model=DEFAULT_MODEL
    )
    
    # Register SQLite client
    sqlite_client = user_clients.get(username)
    if sqlite_client:
        agent.register_mcp_client("SQLite", sqlite_client)
    
    # Register Notion clients
    if username in user_notion_clients:
        for workspace_id, notion_client in user_notion_clients[username].items():
            agent.register_mcp_client(f"Notion_{workspace_id}", notion_client)
    
    # Hydrate conversation history
    await hydrate_agent_if_empty(username, session_id, agent)
    
    # Process message
    response = await agent.chat(req.message)
    
    # Save messages to database
    # ... (existing save logic)
    
    return {
        "response": response["content"],
        "tool_calls": response.get("tool_calls", []),
        "servers_used": list(agent.mcp_clients.keys())
    }
```

---

### **Phase 4: Frontend Dynamic Inputs**

#### **Step 4.1: Add Notion UI to Sidebar**

**File:** `static/index.html` (update sidebar)

```html
<!-- Existing SQLite controls -->
<div class="control-group">
    <label>🗄️ SQLite Connection</label>
    <button id="connectBtn" onclick="connect()">Connect to SQLite</button>
</div>

<!-- NEW: Notion controls -->
<div class="control-group">
    <label>📝 Notion Connection</label>
    <button onclick="connectNotion()">Connect Notion Workspace</button>
    <div id="notionWorkspaces"></div>
</div>

<!-- NEW: Notion dynamic inputs -->
<div class="control-group" id="notionInputs" style="display:none;">
    <label>🔍 Notion Query</label>
    
    <select id="notionAction">
        <option value="list_databases">List Databases</option>
        <option value="query_database">Query Database</option>
        <option value="search">Search Workspace</option>
        <option value="create_page">Create Page</option>
    </select>
    
    <div id="dynamicNotionFields"></div>
    
    <button onclick="executeNotionAction()">Execute</button>
</div>
```

---

#### **Step 4.2: JavaScript for Dynamic Notion Inputs**

**File:** `static/index.html` (add script)

```javascript
// Notion OAuth
async function connectNotion() {
    try {
        const res = await fetch('/api/notion/auth');
        const data = await res.json();
        
        // Open OAuth popup
        const width = 600, height = 700;
        const left = (screen.width - width) / 2;
        const top = (screen.height - height) / 2;
        
        const popup = window.open(
            data.oauth_url,
            'Notion OAuth',
            `width=${width},height=${height},left=${left},top=${top}`
        );
        
        // Poll for completion
        const checkInterval = setInterval(async () => {
            if (popup.closed) {
                clearInterval(checkInterval);
                await loadNotionWorkspaces();
            }
        }, 1000);
    } catch (error) {
        console.error('Notion auth error:', error);
        alert('Failed to connect to Notion');
    }
}

// Load connected workspaces
async function loadNotionWorkspaces() {
    try {
        const res = await fetch('/api/notion/workspaces');
        const data = await res.json();
        
        const container = document.getElementById('notionWorkspaces');
        container.innerHTML = '';
        
        data.workspaces.forEach(ws => {
            const div = document.createElement('div');
            div.className = 'workspace-item';
            div.innerHTML = `
                <img src="${ws.workspace_icon || '📝'}" width="20">
                <span>${ws.workspace_name}</span>
                <button onclick="connectNotionMCP('${ws.workspace_id}')">Connect</button>
                <button onclick="disconnectNotion('${ws.workspace_id}')">❌</button>
            `;
            container.appendChild(div);
        });
        
        document.getElementById('notionInputs').style.display = 'block';
    } catch (error) {
        console.error('Load workspaces error:', error);
    }
}

// Connect to Notion MCP
async function connectNotionMCP(workspaceId) {
    try {
        const res = await fetch(`/api/notion/connect?workspace_id=${workspaceId}`, {
            method: 'POST'
        });
        const data = await res.json();
        
        if (data.status === 'connected') {
            alert(`Connected to Notion workspace!\nAvailable tools: ${data.tools.length}`);
            
            // Show Notion tools in UI
            displayNotionTools(data.tools);
        }
    } catch (error) {
        console.error('Connect error:', error);
        alert('Failed to connect to Notion MCP');
    }
}

// Dynamic field generation based on action
document.getElementById('notionAction')?.addEventListener('change', (e) => {
    const action = e.target.value;
    const fieldsDiv = document.getElementById('dynamicNotionFields');
    
    fieldsDiv.innerHTML = '';
    
    switch(action) {
        case 'query_database':
            fieldsDiv.innerHTML = `
                <label>Database ID:</label>
                <input type="text" id="databaseId" placeholder="Enter database ID">
                <label>Filter (JSON):</label>
                <textarea id="filterJson" rows="3" placeholder='{"property": "Status", "status": {"equals": "Done"}}'></textarea>
            `;
            break;
        
        case 'search':
            fieldsDiv.innerHTML = `
                <label>Search Query:</label>
                <input type="text" id="searchQuery" placeholder="Enter search terms">
            `;
            break;
        
        case 'create_page':
            fieldsDiv.innerHTML = `
                <label>Parent Page/Database ID:</label>
                <input type="text" id="parentId" placeholder="Enter parent ID">
                <label>Title:</label>
                <input type="text" id="pageTitle" placeholder="Page title">
                <label>Content (Markdown):</label>
                <textarea id="pageContent" rows="5"></textarea>
            `;
            break;
    }
});

// Execute Notion action
async function executeNotionAction() {
    const action = document.getElementById('notionAction').value;
    
    let message = '';
    
    switch(action) {
        case 'list_databases':
            message = 'List all my Notion databases';
            break;
        
        case 'query_database':
            const dbId = document.getElementById('databaseId').value;
            const filter = document.getElementById('filterJson').value;
            message = `Query Notion database ${dbId} with filter: ${filter}`;
            break;
        
        case 'search':
            const query = document.getElementById('searchQuery').value;
            message = `Search Notion workspace for: ${query}`;
            break;
        
        case 'create_page':
            const parentId = document.getElementById('parentId').value;
            const title = document.getElementById('pageTitle').value;
            const content = document.getElementById('pageContent').value;
            message = `Create Notion page titled "${title}" in ${parentId} with content: ${content}`;
            break;
    }
    
    // Send to chat
    await sendMessage(message);
}

// Enhanced sendMessage to support multi-server
async function sendMessage(text) {
    const message = text || document.getElementById('messageInput').value.trim();
    if (!message) return;
    
    // Use multi-server endpoint
    const res = await fetch('/api/chat/multi', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: message})
    });
    
    const data = await res.json();
    
    // Display response
    displayMessage('user', message);
    displayMessage('assistant', data.response, data.tool_calls, data.servers_used);
    
    document.getElementById('messageInput').value = '';
}
```

---

### **Phase 5: Notion Tool Examples**

#### **Available Notion MCP Tools (from API docs)**

1. **`list_databases`** - List all accessible databases
   ```json
   {
     "name": "list_databases",
     "arguments": {}
   }
   ```

2. **`get_database`** - Get specific database info
   ```json
   {
     "name": "get_database",
     "arguments": {
       "database_id": "668d797c-76fa-4934-9b05-ad288df2d136"
     }
   }
   ```

3. **`query_database`** - Query database entries
   ```json
   {
     "name": "query_database",
     "arguments": {
       "database_id": "668d797c-76fa-4934-9b05-ad288df2d136",
       "filter": {
         "property": "Status",
         "status": {"equals": "In Progress"}
       },
       "sorts": [
         {"property": "Created", "direction": "descending"}
       ]
     }
   }
   ```

4. **`search_pages`** - Search workspace
   ```json
   {
     "name": "search_pages",
     "arguments": {
       "query": "project roadmap",
       "filter": {"property": "object", "value": "page"}
     }
   }
   ```

5. **`create_page`** - Create new page
   ```json
   {
     "name": "create_page",
     "arguments": {
       "parent": {"database_id": "..."},
       "properties": {
         "Name": {"title": [{"text": {"content": "New Task"}}]}
       },
       "children": [...]
     }
   }
   ```

---

## 🔐 **Security Considerations**

### **1. OAuth Token Security**
- ✅ Store tokens encrypted in database
- ✅ Use HTTP-only cookies for sessions
- ✅ Implement CSRF protection (state parameter)
- ✅ Token expiration and refresh

### **2. Per-User Isolation**
- ✅ Each user has separate Notion tokens
- ✅ Workspace access controlled by Notion OAuth scopes
- ✅ No cross-user data leakage

### **3. MCP Connection Security**
- ✅ Use HTTPS for remote MCP (Notion provides this)
- ✅ Validate OAuth tokens before tool execution
- ✅ Rate limiting on Notion API calls

---

## 🧪 **Testing Plan**

### **Test Case 1: OAuth Flow**
1. Click "Connect Notion Workspace"
2. Authorize in Notion OAuth popup
3. Verify token stored in database
4. Check workspace appears in UI

### **Test Case 2: Database Listing**
1. Connect to Notion workspace
2. Send message: "List my Notion databases"
3. LLM calls `list_databases` tool
4. Verify databases displayed

### **Test Case 3: Database Query**
1. Input database ID in UI
2. Add filter JSON
3. Click "Execute"
4. Message sent: "Query database X with filter Y"
5. LLM executes query, returns results

### **Test Case 4: Multi-Server Chat**
1. Connect both SQLite and Notion
2. Ask: "How many users in SQLite and databases in Notion?"
3. LLM calls tools from both servers
4. Verify combined response

### **Test Case 5: Page Creation**
1. Fill in parent ID, title, content
2. Click "Execute"
3. LLM creates Notion page
4. Verify page exists in Notion workspace

---

## 📦 **Dependencies**

Add to `requirements.txt`:

```txt
# Existing
fastapi>=0.104.1
uvicorn[standard]>=0.24.0
httpx>=0.25.1
mcp>=1.0.0
python-dotenv>=1.0.0

# NEW (if not already present)
pydantic>=2.5.0
aiosqlite>=0.19.0
```

---

## 🚀 **Deployment Checklist**

- [ ] Register Notion OAuth integration at https://www.notion.so/my-integrations
- [ ] Set `NOTION_CLIENT_ID` and `NOTION_CLIENT_SECRET` in `.env`
- [ ] Update database schema (add `notion_tokens` table)
- [ ] Create `notion_mcp_client.py`
- [ ] Update `llm_integration.py` for multi-server support
- [ ] Add Notion endpoints to `fastapi_app_fixed.py`
- [ ] Update frontend HTML with Notion UI
- [ ] Test OAuth flow end-to-end
- [ ] Test tool execution with real Notion workspace
- [ ] Add error handling and user feedback
- [ ] Document API endpoints

---

## 📚 **User Guide (Example)**

### **Connecting Notion**

1. Click "Connect Notion Workspace" in sidebar
2. Authorize your Notion workspace
3. Workspace appears in connected list
4. Click "Connect" to activate MCP connection

### **Querying Databases**

**Natural Language:**
```
"Show me all tasks in my Project database where Status is 'In Progress'"
```

**Dynamic Form:**
1. Select "Query Database" from dropdown
2. Paste database ID
3. Enter filter JSON:
   ```json
   {"property": "Status", "status": {"equals": "In Progress"}}
   ```
4. Click "Execute"

### **Creating Pages**

**Natural Language:**
```
"Create a new page titled 'Meeting Notes' in my Work database with today's agenda"
```

**Dynamic Form:**
1. Select "Create Page"
2. Enter parent database ID
3. Enter title and content
4. Click "Execute"

---

## 🎯 **Next Steps**

1. **Implement Phase 1** (OAuth backend)
2. **Test OAuth flow** with real Notion account
3. **Implement Phase 2** (Notion MCP client)
4. **Test tool discovery** and basic calls
5. **Implement Phase 3** (Multi-server LLM agent)
6. **Test combined SQLite + Notion queries**
7. **Implement Phase 4** (Frontend UI)
8. **End-to-end testing** with dynamic inputs
9. **Polish UI/UX** and error handling
10. **Document for users**

---

## 📖 **Additional Resources**

- **Notion MCP Docs:** https://developers.notion.com/docs/mcp
- **Notion API Reference:** https://developers.notion.com/reference/intro
- **OAuth Guide:** https://developers.notion.com/docs/authorization
- **MCP Protocol:** https://modelcontextprotocol.io/
- **Your existing docs:** `LLM_INTEGRATED.md`, `AUTHENTICATION_IMPLEMENTATION.md`

---

## ✅ **Summary**

This plan enables users to:

✅ **Authenticate** with Notion via OAuth  
✅ **Connect** multiple Notion workspaces dynamically  
✅ **Query** databases with natural language or structured forms  
✅ **Create/update** pages and content  
✅ **Use both SQLite and Notion** in the same chat  
✅ **Provide dynamic inputs** from the frontend for precise control  

**Architecture:** Modular, per-user isolated, secure OAuth, multi-server LLM agent  
**Frontend:** Clean UI with dynamic forms for Notion operations  
**Backend:** FastAPI endpoints for OAuth, token storage, MCP management  

---

**Ready to implement? Let's start with Phase 1! 🚀**
