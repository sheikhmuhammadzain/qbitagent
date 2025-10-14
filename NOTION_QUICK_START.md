# ⚡ Notion MCP - Quick Start Guide

> **5-minute setup** to connect Notion to your MCP Database Assistant

---

## 🚀 **Quick Setup (3 Steps)**

### 1. Register Notion Integration (2 minutes)

1. Go to: **https://www.notion.so/my-integrations**
2. Click **"+ New integration"**
3. Name: `MCP Database Assistant`
4. Add redirect URI: `http://localhost:8000/api/notion/callback`
5. Click **Submit**
6. Copy the **OAuth client ID** and **OAuth client secret**

### 2. Update .env (30 seconds)

Add to your `.env` file:

```env
NOTION_CLIENT_ID=paste-your-client-id-here
NOTION_CLIENT_SECRET=paste-your-client-secret-here
```

### 3. Restart Server (30 seconds)

```bash
python run_fixed.py
```

---

## ✅ **Verify It Works**

### Test 1: Check OAuth is configured

```bash
curl http://localhost:8000/api/notion/auth
```

Expected: `{"oauth_url": "https://api.notion.com/v1/oauth/authorize?..."}`

### Test 2: Complete OAuth flow

1. Open the `oauth_url` from above in your browser
2. Select your Notion workspace
3. Click "Select pages" and choose databases to share
4. Click "Allow access"

---

## 💬 **Start Using**

Once connected, just chat normally:

```
"List my Notion databases"

"Show tasks from my Project Tracker where Status is In Progress"

"How many users in SQLite and databases in Notion?"
```

The AI will automatically use both SQLite and Notion!

---

## 📚 **Full Documentation**

- **Setup Guide:** `NOTION_SETUP.md` (detailed instructions + troubleshooting)
- **Implementation:** `NOTION_IMPLEMENTATION_SUMMARY.md` (technical overview)
- **API Reference:** See summary file for all endpoints

---

## 🐛 **Troubleshooting**

### "Notion OAuth not configured"
→ Check `.env` has `NOTION_CLIENT_ID` and `NOTION_CLIENT_SECRET`, then restart

### "OAuth token exchange failed"
→ Verify redirect URI in Notion integration matches: `http://localhost:8000/api/notion/callback`

### "No databases showing up"
→ In Notion, share databases with your integration (Database → ... → Connections → Add integration)

---

## 🎯 **What's Possible**

✅ Query Notion databases with natural language  
✅ Search across all Notion pages  
✅ Create and update Notion content  
✅ Use SQLite and Notion in same conversation  
✅ Connect multiple workspaces  

---

## 🔒 **Security Notes**

- OAuth tokens stored securely per-user
- CSRF protection on OAuth flow
- Session-based authentication
- Never commit `.env` to version control

---

**That's it! You're ready to use Notion MCP. 🎉**

For advanced usage and troubleshooting, see `NOTION_SETUP.md`
