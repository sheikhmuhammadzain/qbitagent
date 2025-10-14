"""
Launch script for FIXED FastAPI MCP Client
"""
import uvicorn
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    print("=" * 60)
    print("Starting FIXED FastAPI MCP Client")
    print("=" * 60)
    print("API: http://localhost:8000")
    print("Web UI: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("=" * 60)
    print("This version uses proper MCP SDK patterns!")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    uvicorn.run(
        "fastapi_app_fixed:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
