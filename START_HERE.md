# 🚀 Quick Start Guide

## ✅ Which Startup Script to Use?

### **Windows Users:**

Both scripts now work on Windows! Choose based on your needs:

#### Option 1: `run_fixed.py` (Recommended for Windows)
```powershell
python run_fixed.py
```
- ✅ Works on Windows, Linux, and Mac
- ✅ Auto-reload **disabled on Windows** (for stability)
- ✅ Auto-reload **enabled on Linux/Mac** (for development)
- ✅ Cross-platform compatible

#### Option 2: `run_windows.py` (Windows-Only, Maximum Stability)
```powershell
python run_windows.py
```
- ✅ Windows-optimized startup
- ✅ Maximum stability
- ✅ Shows detailed event loop diagnostics
- ❌ Only for Windows

#### Option 3: Batch Script (Easiest for Windows)
```powershell
START_WINDOWS.bat
```
- ✅ Double-click to start
- ✅ Automatically kills old processes
- ✅ No command line needed

---

## 📋 Complete Startup Instructions

### 1️⃣ **First Time Setup**

```powershell
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env and add your API key
notepad .env
```

Add this line:
```
OPENROUTER_API_KEY=your-key-here
```

### 2️⃣ **Start Backend** (Port 8000)

**Windows:**
```powershell
python run_fixed.py
```

**Linux/Mac:**
```bash
python3 run_fixed.py
```

You should see:
```
================================================================================
WINDOWS DETECTED - Configuring ProactorEventLoop
================================================================================
✅ Policy: WindowsProactorEventLoopPolicy
✅ Loop: ProactorEventLoop
✅ Is ProactorEventLoop: True
================================================================================
Backend API: http://localhost:8000
React Frontend: http://localhost:8080
```

### 3️⃣ **Start Frontend** (Port 8080) - Optional

If using the React frontend:

```powershell
cd client
npm install  # First time only
npm run dev
```

Then open: http://localhost:8080

---

## 🧪 Test Everything Works

Run the comprehensive test suite:

```powershell
python test_all_endpoints.py
```

This tests:
- ✅ Server health
- ✅ Authentication
- ✅ MCP server connection (SQLite)
- ✅ Database queries
- ✅ Chat functionality
- ✅ File uploads

---

## ❌ Troubleshooting

### Problem: "NotImplementedError" when connecting to database

**Symptom:**
```
ERROR: NotImplementedError
File "asyncio\base_events.py", line 502, in _make_subprocess_transport
```

**Solution:**
1. Stop the server completely (Ctrl+C)
2. Kill all Python processes: `taskkill /F /IM python.exe`
3. Restart with: `python run_fixed.py`

**Why it happens:** 
- The wrong event loop type is active
- Happens when using auto-reload on Windows
- Fixed by disabling reload on Windows

---

### Problem: Port already in use

**Symptom:**
```
ERROR: [Errno 10048] Only one usage of each socket address
```

**Solution:**
```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace <PID> with actual number)
taskkill /F /PID <PID>

# Or kill all Python processes
taskkill /F /IM python.exe
```

---

### Problem: Module not found

**Symptom:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```powershell
# Make sure you're in the project directory
cd "C:\Users\ibrahim laptops\Desktop\mcp-server"

# Activate virtual environment if you have one
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🎯 Quick Reference

| Script | Platform | Reload | Best For |
|--------|----------|--------|----------|
| `run_fixed.py` | All | Auto (disabled on Windows) | **Recommended** |
| `run_windows.py` | Windows only | No | Maximum stability |
| `START_WINDOWS.bat` | Windows only | No | Easiest (double-click) |

---

## 🔗 Useful URLs

- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs
- **Frontend (if running):** http://localhost:8080

---

## 📚 More Documentation

- `README.md` - Main documentation
- `PRODUCTION_DEPLOYMENT.md` - Production server setup
- `WINDOWS_FIX.md` - Windows event loop issue details
- `PROJECT_STRUCTURE.md` - File structure explanation

---

## 🆘 Need Help?

1. Check the logs in the terminal
2. Run `python test_all_endpoints.py` to diagnose issues
3. Check if ports 8000/8080 are available
4. Verify `.env` file has `OPENROUTER_API_KEY`
5. Make sure Python 3.11+ is installed: `python --version`

---

**Made with ❤️ using FastAPI + MCP + OpenRouter**
