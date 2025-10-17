"""
Diagnostic script to test database switching
Run this to debug the database switch error
"""
import sys
import os
from pathlib import Path
import asyncio

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_database_switch():
    """Test database switching with detailed logging"""
    
    # Test database path (adjust this to your actual failing database path)
    db_path = "uploads/zain/databases/b56d30ef-8849-4ebf-83cf-8be1ee392a75.db"
    
    print("=" * 80)
    print("DATABASE SWITCH DIAGNOSTIC TEST")
    print("=" * 80)
    
    # 1. Check if database file exists
    print(f"\n1. Checking database file...")
    print(f"   Path: {db_path}")
    resolved_path = Path(db_path).resolve()
    print(f"   Resolved: {resolved_path}")
    print(f"   Exists: {resolved_path.exists()}")
    
    if not resolved_path.exists():
        print(f"   ❌ ERROR: Database file does not exist!")
        return False
    else:
        print(f"   ✅ Database file exists")
        print(f"   Size: {resolved_path.stat().st_size:,} bytes")
    
    # 2. Check SQLite MCP server script
    print(f"\n2. Checking SQLite MCP server script...")
    current_dir = Path(__file__).parent.resolve()
    sqlite_server_script = current_dir / "sqlite_mcp_fastmcp.py"
    print(f"   Script path: {sqlite_server_script}")
    print(f"   Exists: {sqlite_server_script.exists()}")
    
    if not sqlite_server_script.exists():
        print(f"   ❌ ERROR: SQLite MCP server script not found!")
        return False
    else:
        print(f"   ✅ SQLite MCP server script exists")
    
    # 3. Check Python executable
    print(f"\n3. Checking Python executable...")
    python_exe = sys.executable
    print(f"   Python: {python_exe}")
    print(f"   Version: {sys.version}")
    print(f"   Exists: {Path(python_exe).exists()}")
    
    # 4. Test MCP imports
    print(f"\n4. Testing MCP imports...")
    try:
        from mcp import StdioServerParameters
        from mcp_client_fixed import MCPClient
        print(f"   ✅ MCP imports successful")
    except Exception as e:
        print(f"   ❌ ERROR importing MCP: {e}")
        return False
    
    # 5. Create server config
    print(f"\n5. Creating server configuration...")
    try:
        server_config = StdioServerParameters(
            command=python_exe,
            args=["-u", str(sqlite_server_script), str(resolved_path)],
            env=os.environ.copy()
        )
        print(f"   Command: {server_config.command}")
        print(f"   Args: {server_config.args}")
        print(f"   Env: {'SET' if server_config.env else 'None'}")
        print(f"   ✅ Server config created")
    except Exception as e:
        print(f"   ❌ ERROR creating server config: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. Try to connect to MCP server
    print(f"\n6. Testing MCP server connection...")
    print(f"   This will spawn the SQLite MCP server subprocess...")
    
    client = None
    try:
        client = MCPClient(server_config)
        print(f"   MCPClient created")
        
        print(f"   Attempting to connect (this may take a few seconds)...")
        await client.connect()
        print(f"   ✅ Successfully connected to MCP server!")
        
        # 7. List available tools
        print(f"\n7. Testing tool listing...")
        tools = await client.list_tools()
        print(f"   ✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"      - {tool.name}")
        
        # 8. Test a simple query
        print(f"\n8. Testing database query...")
        result = await client.call_tool("list_tables", {})
        print(f"   ✅ Query successful!")
        print(f"   Result: {result.result[:200]}...")  # First 200 chars
        
        print(f"\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"   ❌ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"\nFull traceback:")
        traceback.print_exc()
        
        print(f"\n" + "=" * 80)
        print("❌ TEST FAILED!")
        print("=" * 80)
        return False
        
    finally:
        if client:
            print(f"\nClosing MCP client...")
            await client.close()
            print(f"Client closed")


async def test_manual_subprocess():
    """Test spawning the SQLite server subprocess manually"""
    import subprocess
    
    print("\n" + "=" * 80)
    print("MANUAL SUBPROCESS TEST")
    print("=" * 80)
    
    db_path = "uploads/zain/databases/b56d30ef-8849-4ebf-83cf-8be1ee392a75.db"
    resolved_path = Path(db_path).resolve()
    current_dir = Path(__file__).parent.resolve()
    sqlite_server_script = current_dir / "sqlite_mcp_fastmcp.py"
    python_exe = sys.executable
    
    cmd = [python_exe, "-u", str(sqlite_server_script), str(resolved_path)]
    
    print(f"Command: {' '.join(cmd)}")
    print(f"\nAttempting to start subprocess...")
    print(f"(Will run for 3 seconds then terminate)\n")
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy()
        )
        
        # Wait a bit and check if it's still running
        import time
        time.sleep(3)
        
        if proc.poll() is None:
            print("✅ Subprocess is running!")
            proc.terminate()
            proc.wait(timeout=5)
            print("✅ Subprocess terminated successfully")
            return True
        else:
            print(f"❌ Subprocess exited with code: {proc.returncode}")
            stdout, stderr = proc.communicate()
            print(f"\nSTDOUT:\n{stdout}")
            print(f"\nSTDERR:\n{stderr}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\nStarting diagnostic tests...\n")
    
    # Adjust this path to match your failing database
    print("IMPORTANT: Edit line 19 in this script to use your actual database path!")
    print("Current test path: uploads/zain/databases/b56d30ef-8849-4ebf-83cf-8be1ee392a75.db\n")
    
    # Run async test
    result1 = asyncio.run(test_database_switch())
    
    # Run manual subprocess test
    result2 = asyncio.run(test_manual_subprocess())
    
    if result1 and result2:
        print("\n✅ All diagnostics passed! The issue might be elsewhere.")
    else:
        print("\n❌ Some diagnostics failed. Check the errors above.")
