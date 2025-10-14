# 🤖 AI-Powered SQLite Database Assistant

A complete AI agent that uses OpenRouter LLMs with MCP (Model Context Protocol) to interact with SQLite databases through natural language.

## ✨ Features

- 🧠 **OpenRouter Integration** - Uses GLM-4-Flash (free!) or other models
- 🔧 **Intelligent Tool Calling** - LLM automatically selects and uses database tools
- 🔄 **Multi-Step Reasoning** - Handles complex queries with multiple operations
- 💬 **Conversation Memory** - Maintains context across chat history
- 🎨 **Beautiful Web UI** - Clean, modern interface
- ⚡ **FastAPI Backend** - Fast, async API server
- 🔌 **MCP Protocol** - Standard protocol for LLM-tool communication

## 🚀 Quick Start

### 1. Install Dependencies

```powershell
pip install fastapi uvicorn python-dotenv mcp httpx
```

### 2. Set Up Environment

Create a `.env` file:

```env
OPENROUTER_API_KEY=your-api-key-here
DEFAULT_MODEL=z-ai/glm-4.5-air:free
```

Get your free API key at: https://openrouter.ai/

### 3. Run the Application

```powershell
python run_fixed.py
```

This will:
- Start the FastAPI server on `http://localhost:8000`
- Automatically open your browser
- Set up the SQLite database

### 4. Start Chatting!

1. Click "Connect to MCP Server"
2. Ask questions like:
   - "What tables are in the database?"
   - "Show me 5 users"
   - "Create a user named Alice with email alice@example.com"
   - "How many users do we have?"

## 📁 Project Structure

```
mcp-server/
├── run_fixed.py              # Main launcher script
├── fastapi_app_fixed.py      # FastAPI server with all endpoints
├── llm_integration.py        # OpenRouter LLM agent with tool calling
├── mcp_client_fixed.py       # MCP client for server communication
├── sqlite_mcp_fastmcp.py     # SQLite MCP server (FastMCP SDK)
├── setup_database.py         # Database initialization
├── config.py                 # Configuration settings
├── static/
│   └── index.html            # Web UI
├── .env                      # Environment variables (you create this)
└── test.db                   # SQLite database (auto-generated)
```

## 🎯 How It Works

```
User Question
    ↓
Web UI (HTML)
    ↓
FastAPI Server
    ↓
LLM Agent (OpenRouter)
    ↓
Tool Selection & Execution
    ↓
MCP Client
    ↓
SQLite MCP Server
    ↓
Database Results
    ↓
Natural Language Response
```

## 🛠️ Available Database Tools

The LLM can use these 8 tools automatically:

1. **list_tables** - List all database tables
2. **describe_table** - Get table schema/structure
3. **execute_query** - Run any SQL SELECT query
4. **get_database_info** - Get database metadata
5. **create_user** - Add a new user
6. **list_users** - Show all users
7. **update_user** - Modify user details
8. **delete_user** - Remove a user

## 🌐 API Endpoints

### Connect to MCP Server
```http
POST /api/connect
Content-Type: application/json

{
  "server_name": "SQLite",
  "model": "z-ai/glm-4.5-air:free"
}
```

### Chat with AI Agent
```http
POST /api/chat
Content-Type: application/json

{
  "message": "What tables exist in the database?"
}
```

### Disconnect
```http
POST /api/disconnect
```

### Check Status
```http
GET /api/status
```

## 💡 Example Usage

### Python

```python
import requests

API = "http://localhost:8000"

# Connect
requests.post(f"{API}/api/connect", json={
    "server_name": "SQLite",
    "model": "z-ai/glm-4.5-air:free"
})

# Chat
response = requests.post(f"{API}/api/chat", json={
    "message": "Show me the database structure"
})

print(response.json()["response"])
```

### JavaScript

```javascript
// Connect
await fetch('http://localhost:8000/api/connect', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        server_name: 'SQLite',
        model: 'z-ai/glm-4.5-air:free'
    })
});

// Chat
const res = await fetch('http://localhost:8000/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        message: 'List all users'
    })
});

const data = await res.json();
console.log(data.response);
```

## 🎨 Supported LLM Models

- **z-ai/glm-4.5-air:free** (Default, FREE!)
- **anthropic/claude-3.5-sonnet**
- **openai/gpt-4-turbo**
- **google/gemini-pro**

Change models in the UI dropdown or via API.

## 📖 Documentation

For detailed documentation, see [LLM_INTEGRATED.md](LLM_INTEGRATED.md) which includes:

- Detailed architecture explanation
- Example conversations
- Troubleshooting guide
- Performance tips
- Production deployment advice

## 🔧 Troubleshooting

### "Connection failed"
- Check your OPENROUTER_API_KEY in `.env`
- Verify internet connection
- Make sure API key is valid

### "Tool execution failed"
- Ensure SQLite server is connected
- Check if database file exists
- Verify SQL syntax if using execute_query

### Slow responses
- Normal for first request (3-5 seconds)
- Complex queries take longer (5-10 seconds)
- GLM-4-Flash is already the fastest model

## 🤝 Contributing

This is a demonstration project. Feel free to:
- Add more MCP tools
- Support other databases (PostgreSQL, MySQL)
- Add streaming responses
- Implement user authentication
- Add response caching

## 📄 License

MIT License - Feel free to use and modify!

## 🙏 Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol
- [OpenRouter](https://openrouter.ai/) - LLM API gateway
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP SDK for Python

---

**Made with ❤️ using AI and MCP**

Need help? Check [LLM_INTEGRATED.md](LLM_INTEGRATED.md) for detailed docs!
