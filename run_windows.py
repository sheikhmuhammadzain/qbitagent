"""
Windows-specific launch script that forces ProactorEventLoop BEFORE uvicorn starts
Use this on Windows if run_fixed.py doesn't work
"""
import sys
import asyncio
import logging

# CRITICAL: Set event loop policy BEFORE any async operations
if sys.platform == 'win32':
    print("=" * 80)
    print("WINDOWS STARTUP - Setting ProactorEventLoop Policy")
    print("=" * 80)
    
    # Force ProactorEventLoop policy
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Create and set a new ProactorEventLoop
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    
    print(f"✅ Policy: {type(asyncio.get_event_loop_policy()).__name__}")
    print(f"✅ Loop: {type(asyncio.get_event_loop()).__name__}")
    print(f"✅ Is ProactorEventLoop: {isinstance(loop, asyncio.ProactorEventLoop)}")
    print("=" * 80)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 80)
    print("Starting FastAPI MCP Server (Windows Optimized)")
    print("=" * 80)
    print("Backend API: http://localhost:8000")
    print("React Frontend: http://localhost:8080")
    print("API Docs: http://localhost:8000/docs")
    print("=" * 80)
    print("NOTE: If using React frontend, also run:")
    print("  cd client && npm run dev")
    print("=" * 80)
    print("Press Ctrl+C to stop")
    print("=" * 80 + "\n")
    
    # Run uvicorn with the existing event loop
    config = uvicorn.Config(
        app="fastapi_app_fixed:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload to prevent loop recreation
        log_level="info",
        loop="asyncio"  # Use asyncio loop (our custom one)
    )
    
    server = uvicorn.Server(config)
    
    # Run with our pre-configured event loop
    if sys.platform == 'win32':
        loop.run_until_complete(server.serve())
    else:
        asyncio.run(server.serve())
