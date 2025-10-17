"""
Launch script for FIXED FastAPI MCP Client
"""
import uvicorn
import logging
import sys
import asyncio

# Fix for Windows: Set ProactorEventLoop policy to support subprocesses
if sys.platform == 'win32':
    print("=" * 80)
    print("WINDOWS DETECTED - Configuring ProactorEventLoop")
    print("=" * 80)
    # Use ProactorEventLoop on Windows for subprocess support
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    # Create and set new loop
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    print(f"✅ Policy: {type(asyncio.get_event_loop_policy()).__name__}")
    print(f"✅ Loop: {type(asyncio.get_event_loop()).__name__}")
    print(f"✅ Is ProactorEventLoop: {isinstance(loop, asyncio.ProactorEventLoop)}")
    print("=" * 80)
    logging.info("✅ Set Windows ProactorEventLoop policy for subprocess support")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    print("=" * 60)
    print("Starting FIXED FastAPI MCP Client")
    print("=" * 60)
    print("Backend API: http://localhost:8000")
    print("React Frontend: http://localhost:8080")
    print("API Docs: http://localhost:8000/docs")
    print("=" * 60)
    print("NOTE: If using React frontend, also run:")
    print("  cd client && npm run dev")
    print("=" * 60)
    print("This version uses proper MCP SDK patterns!")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    # Configure uvicorn with correct event loop for Windows
    config_kwargs = {
        "app": "fastapi_app_fixed:app",
        "host": "0.0.0.0",
        "reload": False,
        "port": 8090,
        "log_level": "info"
    }
    
    # Disable reload on all platforms - it breaks MCP subprocess connections
    # The uvicorn reloader creates a subprocess which interferes with MCP client subprocesses
    config_kwargs["reload"] = False
    
    if sys.platform == 'win32':
        config_kwargs["loop"] = "asyncio"
        print("✅ Windows: Using ProactorEventLoop (reload disabled for stability)")
        print("=" * 60)
    else:
        print("✅ Linux/Mac: Reload disabled to support MCP subprocess tools")
        print("=" * 60)
    
    uvicorn.run(**config_kwargs)
