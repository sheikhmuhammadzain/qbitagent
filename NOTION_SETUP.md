# 🚀 Notion MCP Integration - Setup Guide

## 📋 Overview

This guide will walk you through setting up and using the Notion MCP integration with your MCP Database Assistant. Once configured, you'll be able to:

- ✅ Connect multiple Notion workspaces
- ✅ Query Notion databases with natural language
- ✅ Search across your Notion pages
- ✅ Create and update Notion content
- ✅ Use SQLite and Notion together in the same conversation

---

## 🔧 Prerequisites

1. **Existing MCP Database Assistant** - Already set up and working
2. **Notion Account** - Free or paid Notion account
3. **OpenRouter API Key** - Already configured in `.env`

---

## 📝 Step 1: Register Notion OAuth Integration

### 1.1 Create Integration

1. Go to **https://www.notion.so/my-integrations**
2. Click **"+ New integration"**
3. Fill in the details:
   - **Name:** MCP Database Assistant
   - **Logo:** (Optional)
   - **Associated workspace:** Choose your workspace

### 1.2 Configure OAuth

1. Under **"Capabilities"**, ensure these are enabled:
   - ✅ Read content
   - ✅ Update content
   - ✅ Insert content

2. Under **"Integration type"**, select:
   - ⚪ **Public integration** (recommended)

3. Under **"Redirect URIs"**, add:
   ```
   http://localhost:8000/api/notion/callback
   ```
   
   For production, also add:
   ```
   https://yourdomain.com/api/notion/callback
   ```

4. Click **"Submit"**

### 1.3 Get Credentials

After submission, you'll see:
- **OAuth client ID** (e.g., `1234567890abcdef...`)
- **OAuth client secret** (click "Show" to reveal)

**Important:** Keep these credentials secret!

---

## 🔐 Step 2: Configure Environment Variables

### 2.1 Update `.env` File

Add these lines to your `.env` file:

```env
# Notion OAuth Configuration
NOTION_CLIENT_ID=your-notion-client-id-here
NOTION_CLIENT_SECRET=your-notion-client-secret-here
NOTION_REDIRECT_URI=http://localhost:8000/api/notion/callback
```

Replace `your-notion-client-id-here` and `your-notion-client-secret-here` with your actual credentials.

### 2.2 Optional Settings

You can also configure:

```env
# Custom Notion MCP URL (default: https://mcp.notion.com/mcp)
NOTION_MCP_URL=https://mcp.notion.com/mcp

# Session secret for cookies (change in production!)
SESSION_SECRET=your-strong-random-secret-key-here
```

---

## 🚀 Step 3: Restart the Server

After updating `.env`, restart your FastAPI server:

```powershell
python run_fixed.py
```

Or if running manually:

```powershell
uvicorn fastapi_app_fixed:app --reload
```

Check the logs for:
```
✅ Database initialized successfully
INFO:     Application startup complete.
```

---

## 🎯 Step 4: Connect Notion from UI

### 4.1 Sign In

1. Open **http://localhost:8000**
2. Sign in with your username/password

### 4.2 Connect Notion Workspace

1. In the sidebar, find **"📝 Notion Connection"**
2. Click **"Connect Notion Workspace"**
3. A popup window will open showing Notion's OAuth page
4. Select the workspace you want to connect
5. Click **"Select pages"** and choose which pages/databases to share
6. Click **"Allow access"**

### 4.3 Verify Connection

After authorizing:
- The popup will close automatically
- Your workspace should appear in the sidebar
- Click **"Connect"** next to the workspace name
- You'll see a success message with the number of tools available

---

## 💬 Step 5: Start Using Notion

### 5.1 Natural Language Queries

Simply type your questions in the chat:

```
List all my Notion databases
```

```
Show me tasks from my Project Tracker database where status is 'In Progress'
```

```
Search my Notion workspace for 'meeting notes'
```

```
Create a new page titled 'Weekly Report' in my Work database
```

### 5.2 Multi-Server Queries

You can query both SQLite and Notion in the same conversation:

```
How many users are in the SQLite database and how many databases are in Notion?
```

```
Compare the project count in SQLite with tasks in my Notion Project Tracker
```

---

## 🛠️ Available Notion Tools

The LLM has access to these Notion MCP tools:

| Tool | Description | Example Query |
|------|-------------|---------------|
| **list_databases** | List all accessible databases | "Show my Notion databases" |
| **get_database** | Get specific database info | "Tell me about database X" |
| **query_database** | Query database entries | "Show tasks where Status='Done'" |
| **search_pages** | Search workspace | "Find pages about 'project roadmap'" |
| **create_page** | Create new page | "Create a meeting notes page" |
| **update_page** | Update existing page | "Add content to page X" |
| **get_page** | Get page details | "Show me page X" |

---

## 🔍 Advanced Usage

### Using Database IDs

If you know a database ID, you can query it directly:

```
Query Notion database 668d797c-76fa-4934-9b05-ad288df2d136 
with filter: {"property": "Status", "status": {"equals": "In Progress"}}
```

### Filtering and Sorting

The LLM understands complex filters:

```
Show me all tasks from my Projects database created this week, 
sorted by priority
```

### Creating Rich Content

```
Create a new page in my Notes database titled 'Architecture Design'
with content: '# System Overview\n\n## Components\n- API Gateway\n- Database Layer'
```

---

## 🐛 Troubleshooting

### "Notion OAuth not configured"

**Solution:** Make sure `NOTION_CLIENT_ID` and `NOTION_CLIENT_SECRET` are set in `.env` and restart the server.

### "OAuth token exchange failed"

**Possible causes:**
1. Wrong OAuth credentials → Double-check `.env` values
2. Redirect URI mismatch → Verify it matches Notion integration settings
3. Network/firewall issues → Check internet connection

**Solution:** Check server logs for details and verify all settings.

### "Failed to connect to Notion"

**Possible causes:**
1. Invalid or expired OAuth token
2. Network connection issues
3. Notion MCP server unavailable

**Solution:** 
1. Try disconnecting and reconnecting the workspace
2. Check https://mcp.notion.com/mcp is accessible
3. Check server logs for error details

### No databases showing up

**Possible causes:**
1. No databases shared with the integration
2. Workspace permissions issue

**Solution:**
1. In Notion, go to a database → "..." menu → "Connections"
2. Add your integration to the database
3. Reconnect in the app

### Tool calls failing

**Solution:**
1. Check that the workspace is connected (green indicator)
2. Try disconnecting and reconnecting
3. Verify the tool name in server logs
4. Check Notion API status: https://status.notion.so/

---

## 🔒 Security Best Practices

### Development

- ✅ Use different OAuth credentials for dev/prod
- ✅ Never commit `.env` to version control
- ✅ Use `SESSION_SECRET` that's randomly generated

### Production

- ✅ Use HTTPS for all OAuth redirects
- ✅ Update `NOTION_REDIRECT_URI` to your production domain
- ✅ Rotate OAuth credentials periodically
- ✅ Monitor API usage and rate limits
- ✅ Use strong `SESSION_SECRET` (32+ random characters)
- ✅ Enable database encryption
- ✅ Implement proper user permission checks

### Token Storage

- Tokens are stored encrypted in SQLite (`notion_tokens` table)
- Each user has separate tokens (per-user isolation)
- Tokens are session-based with HTTP-only cookies
- CSRF protection via state parameter in OAuth flow

---

## 📊 Architecture

```
┌─────────────────────────────────────────┐
│           Frontend (Browser)            │
│  ┌───────────┐  ┌──────────────────┐  │
│  │ SQLite UI │  │   Notion UI      │  │
│  │           │  │  - OAuth Button  │  │
│  │           │  │  - Workspace List│  │
│  └───────────┘  └──────────────────┘  │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      FastAPI Backend (Python)           │
│  ┌────────────────────────────────────┐ │
│  │ Multi-Server LLM Agent             │ │
│  │ - Routes to SQLite or Notion       │ │
│  │ - Manages multiple connections     │ │
│  └────────────────────────────────────┘ │
│  ┌──────────┐  ┌────────────────────┐  │
│  │ SQLite   │  │ Notion MCP Client  │  │
│  │ MCP      │  │ - OAuth tokens     │  │
│  │ Client   │  │ - Remote HTTP      │  │
│  └──────────┘  └────────────────────┘  │
└─────────────────────────────────────────┘
         ↓                    ↓
┌──────────────┐    ┌──────────────────────┐
│ Local SQLite │    │ Notion Remote MCP    │
│ Database     │    │ https://mcp.notion.com│
└──────────────┘    └──────────────────────┘
```

---

## 📖 API Endpoints

### Notion OAuth

- **GET /api/notion/auth** - Initiate OAuth flow
- **GET /api/notion/callback** - Handle OAuth callback
- **GET /api/notion/workspaces** - List connected workspaces
- **POST /api/notion/connect?workspace_id=X** - Connect to workspace
- **DELETE /api/notion/disconnect/{workspace_id}** - Disconnect workspace

### Multi-Server Chat

- **POST /api/chat/multi** - Chat with SQLite + Notion
  ```json
  {
    "message": "List my Notion databases"
  }
  ```
  Response:
  ```json
  {
    "response": "Here are your Notion databases...",
    "tool_calls": [...],
    "servers_used": ["Notion_workspace123"],
    "timestamp": "2025-01-11T19:00:00"
  }
  ```

---

## 🧪 Testing the Integration

### 1. Test OAuth Flow

```bash
curl http://localhost:8000/api/notion/auth
# Should return: {"oauth_url": "https://api.notion.com/v1/oauth/authorize?..."}
```

### 2. Test Workspace Listing

After connecting:
```bash
curl http://localhost:8000/api/notion/workspaces \
  -H "Cookie: session=your-session-cookie"
# Should return: {"workspaces": [{...}]}
```

### 3. Test Multi-Server Chat

```bash
curl -X POST http://localhost:8000/api/chat/multi \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your-session-cookie" \
  -d '{"message": "List my Notion databases"}'
```

---

## 📚 Further Reading

- **Notion API Docs:** https://developers.notion.com/docs
- **Notion MCP Docs:** https://developers.notion.com/docs/mcp
- **OAuth Guide:** https://developers.notion.com/docs/authorization
- **MCP Protocol:** https://modelcontextprotocol.io/

---

## ✅ Checklist

Before going live:

- [ ] Notion OAuth integration created
- [ ] CLIENT_ID and CLIENT_SECRET in `.env`
- [ ] Redirect URI matches in both places
- [ ] Server restarted after config changes
- [ ] Tested OAuth flow successfully
- [ ] Connected at least one workspace
- [ ] Tested querying Notion databases
- [ ] Tested multi-server chat (SQLite + Notion)
- [ ] Reviewed security best practices
- [ ] Set strong SESSION_SECRET
- [ ] Tested error handling (disconnect/reconnect)

---

## 🆘 Getting Help

If you encounter issues:

1. **Check server logs** for detailed error messages
2. **Verify all environment variables** are set correctly
3. **Test OAuth flow** step by step
4. **Check Notion API status** at https://status.notion.so/
5. **Review this guide** for missed steps

---

## 🎉 Success!

You should now be able to:

✅ Connect multiple Notion workspaces  
✅ Query databases with natural language  
✅ Search and create Notion content  
✅ Use SQLite and Notion together  
✅ Leverage AI to work across both platforms seamlessly  

**Happy querying! 🚀**
