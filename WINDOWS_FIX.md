# 🪟 Windows Asyncio Subprocess Fix

## Problem

On Windows, you may encounter this error when trying to spawn MCP server subprocesses:

```python
NotImplementedError
  File "asyncio\base_events.py", line 502, in _make_subprocess_transport
    raise NotImplementedError
```

## Root Cause

**Windows has special requirements for subprocess handling in asyncio.**

By default, asyncio on Windows uses the `SelectorEventLoop`, which **does not support subprocess operations**. This causes a `NotImplementedError` when trying to create a subprocess (which the MCP client does to spawn the SQLite server).

### Why This Happens:
1. The MCP client spawns a subprocess to run `sqlite_mcp_fastmcp.py`
2. On Windows, asyncio needs `ProactorEventLoop` to handle subprocesses
3. If the wrong event loop policy is active, subprocess creation fails

## Solution

Set the Windows event loop policy to `WindowsProactorEventLoopPolicy` **before** creating any asyncio event loops.

### ✅ Fixed in This Project

The fix has been applied in **two places**:

#### 1. `run_fixed.py` (Line 9-13)
```python
import asyncio
import sys

# Fix for Windows: Set ProactorEventLoop policy to support subprocesses
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

#### 2. `fastapi_app_fixed.py` (Line 12-14)
```python
# Fix for Windows: Set ProactorEventLoop policy to support subprocesses
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

### Why Both Files?

- **`run_fixed.py`**: When starting the server with `python run_fixed.py`
- **`fastapi_app_fixed.py`**: When running directly with `uvicorn fastapi_app_fixed:app`

## Verification

After applying the fix, you should see:

```
✅ Set Windows ProactorEventLoop policy for subprocess support
```

And the MCP server should connect successfully:

```
INFO - Connecting to MCP server: C:\...\python.exe
INFO - Server args: ['-u', 'C:\...\sqlite_mcp_fastmcp.py', ...]
INFO - Stdio transport established
INFO - Client session created
✅ Successfully connected and initialized MCP session
```

## Alternative Workarounds

If you still encounter issues, try these:

### Workaround 1: Run from CMD (not PowerShell)
```cmd
cmd /c python run_fixed.py
```

### Workaround 2: Use Python 3.8+ with Updated Event Loop
Python 3.8+ has better Windows subprocess support. Ensure you're on Python 3.11+.

### Workaround 3: Manually Set Event Loop
```python
# In your code, before any asyncio operations:
import asyncio
import sys

if sys.platform == 'win32':
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
```

## Does This Affect Linux/Mac?

**No!** This fix is Windows-specific:

```python
if sys.platform == 'win32':  # Only on Windows
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

- **Linux/Mac**: Uses `SelectorEventLoop` (which supports subprocesses)
- **Windows**: Uses `ProactorEventLoop` (required for subprocesses)

## Technical Details

### Event Loop Policies on Windows:

| Policy | Subprocess Support | Notes |
|--------|-------------------|-------|
| `WindowsSelectorEventLoopPolicy` | ❌ No | Default in Python < 3.8 |
| `WindowsProactorEventLoopPolicy` | ✅ Yes | **Required for subprocesses** |

### What Changed:
- **Python 3.7 and earlier**: Default was `SelectorEventLoop` (no subprocess support)
- **Python 3.8+**: Default changed to `ProactorEventLoop` on Windows
- **Issue**: Some environments still default to `SelectorEventLoop`

### MCP Protocol Requirements:
The MCP (Model Context Protocol) client uses stdio communication:
1. Spawns subprocess: `python sqlite_mcp_fastmcp.py database.db`
2. Communicates via stdin/stdout
3. **Requires ProactorEventLoop on Windows**

## References

- [Python asyncio subprocess documentation](https://docs.python.org/3/library/asyncio-subprocess.html)
- [Windows ProactorEventLoop](https://docs.python.org/3/library/asyncio-platforms.html#windows)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)

## Summary

✅ **Fix Applied**: Event loop policy set in both `run_fixed.py` and `fastapi_app_fixed.py`  
✅ **Works on**: Windows, Linux, Mac (cross-platform compatible)  
✅ **Result**: MCP server subprocesses now work correctly on Windows  

---

**If you still see subprocess errors after this fix**, please check:
1. Python version (`python --version` should be 3.11+)
2. You're running the correct script (`python run_fixed.py`)
3. No other code is setting a different event loop policy
4. Try restarting your terminal/IDE
