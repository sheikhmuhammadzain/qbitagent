"""
Comprehensive Test Suite for MCP Server
Tests all endpoints and functionality
"""
import asyncio
import sys
import requests
import json
from pathlib import Path
import time

# Configuration
API_BASE = "http://localhost:8000/api"
TEST_USERNAME = f"test_user_{int(time.time())}"
TEST_PASSWORD = "test_password_123"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_test(name):
    print(f"\n{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}TEST: {name}{Colors.END}")
    print(f"{Colors.BLUE}{'='*80}{Colors.END}")

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")

class TestSession:
    def __init__(self):
        self.session = requests.Session()
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def test(self, name, func):
        print_test(name)
        try:
            func()
            self.passed += 1
            print_success(f"{name} PASSED")
            return True
        except AssertionError as e:
            self.failed += 1
            print_error(f"{name} FAILED: {e}")
            return False
        except Exception as e:
            self.failed += 1
            print_error(f"{name} ERROR: {e}")
            return False
    
    def summary(self):
        print(f"\n{'='*80}")
        print(f"{Colors.BOLD}TEST SUMMARY{Colors.END}")
        print(f"{'='*80}")
        print(f"{Colors.GREEN}Passed: {self.passed}{Colors.END}")
        print(f"{Colors.RED}Failed: {self.failed}{Colors.END}")
        print(f"{Colors.YELLOW}Warnings: {self.warnings}{Colors.END}")
        
        total = self.passed + self.failed
        if total > 0:
            success_rate = (self.passed / total) * 100
            print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        if self.failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! 🎉{Colors.END}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}❌ SOME TESTS FAILED ❌{Colors.END}")
        
        print("="*80)

# Initialize test session
test = TestSession()

# ============================================================================
# TEST 1: Server Health Check
# ============================================================================
def test_server_health():
    print_info("Checking if server is running...")
    response = test.session.get(f"{API_BASE}")
    print_info(f"Response: {response.status_code}")
    assert response.status_code == 200, "Server not responding"
    data = response.json()
    print_info(f"Server status: {data.get('status')}")
    assert data.get("status") == "running", "Server not in running state"

test.test("Server Health Check", test_server_health)

# ============================================================================
# TEST 2: Event Loop Check (Critical for Windows)
# ============================================================================
def test_event_loop():
    print_info("Checking event loop configuration...")
    if sys.platform == 'win32':
        print_info("Windows detected - checking for ProactorEventLoop...")
        # This is checked on the server side during connection attempts
        print_warning("Event loop will be verified during MCP connection tests")
    else:
        print_info("Non-Windows platform - event loop check not required")

test.test("Event Loop Configuration", test_event_loop)

# ============================================================================
# TEST 3: Auth - Signup
# ============================================================================
def test_signup():
    print_info(f"Signing up user: {TEST_USERNAME}")
    response = test.session.post(
        f"{API_BASE}/auth/signup",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    print_info(f"Response: {response.status_code}")
    assert response.status_code == 200, f"Signup failed: {response.text}"
    data = response.json()
    print_info(f"Status: {data.get('status')}")
    assert data.get("status") == "signed_up", "Signup status incorrect"

test.test("Auth - Signup", test_signup)

# ============================================================================
# TEST 4: Auth - Me (Check Session)
# ============================================================================
def test_auth_me():
    print_info("Checking current user session...")
    response = test.session.get(f"{API_BASE}/auth/me")
    assert response.status_code == 200, "Auth check failed"
    data = response.json()
    username = data.get("username")
    print_info(f"Current user: {username}")
    assert username == TEST_USERNAME, f"Username mismatch: expected {TEST_USERNAME}, got {username}"

test.test("Auth - Session Check", test_auth_me)

# ============================================================================
# TEST 5: List Available Servers
# ============================================================================
def test_list_servers():
    print_info("Fetching available MCP servers...")
    response = test.session.get(f"{API_BASE}/servers")
    assert response.status_code == 200, "Failed to list servers"
    data = response.json()
    servers = data.get("servers", [])
    print_info(f"Available servers: {', '.join(servers)}")
    assert len(servers) > 0, "No servers available"
    assert "SQLite" in servers, "SQLite server not available"

test.test("List Available Servers", test_list_servers)

# ============================================================================
# TEST 6: List Available Models
# ============================================================================
def test_list_models():
    print_info("Fetching available LLM models...")
    response = test.session.get(f"{API_BASE}/models")
    assert response.status_code == 200, "Failed to list models"
    data = response.json()
    models = data.get("models", [])
    print_info(f"Available models: {len(models)} models")
    for model in models[:3]:  # Show first 3
        print_info(f"  - {model}")

test.test("List Available Models", test_list_models)

# ============================================================================
# TEST 7: Connect to SQLite MCP Server (CRITICAL TEST)
# ============================================================================
def test_connect_sqlite():
    print_info("Attempting to connect to SQLite MCP server...")
    print_info("This is the CRITICAL test for Windows event loop!")
    
    response = test.session.post(
        f"{API_BASE}/connect",
        json={"server_name": "SQLite"}
    )
    
    if response.status_code != 200:
        print_error(f"Connection failed with status {response.status_code}")
        print_error(f"Response: {response.text}")
        
        if "NotImplementedError" in response.text or "event loop" in response.text.lower():
            print_error("="*80)
            print_error("EVENT LOOP ERROR DETECTED!")
            print_error("="*80)
            print_error("The server is using the wrong event loop type.")
            print_error("")
            print_error("SOLUTION:")
            print_error("1. STOP the server (Ctrl+C)")
            print_error("2. Kill all Python: taskkill /F /IM python.exe")
            print_error("3. Start with: python run_windows.py")
            print_error("   OR run: START_WINDOWS.bat")
            print_error("="*80)
        
        raise AssertionError(f"Failed to connect: {response.text}")
    
    data = response.json()
    print_info(f"Status: {data.get('status')}")
    print_info(f"Server: {data.get('server')}")
    print_info(f"Model: {data.get('model')}")
    print_info(f"Tools available: {data.get('tool_count')}")
    
    assert data.get("status") == "connected", "Connection status not 'connected'"
    assert data.get("tool_count", 0) > 0, "No tools available"
    
    # Print available tools
    for tool in data.get("tools", [])[:5]:  # Show first 5 tools
        print_info(f"  Tool: {tool.get('name')}")

test.test("Connect to SQLite MCP Server", test_connect_sqlite)

# ============================================================================
# TEST 8: Check Connection Status
# ============================================================================
def test_connection_status():
    print_info("Checking connection status...")
    response = test.session.get(f"{API_BASE}/status")
    assert response.status_code == 200, "Status check failed"
    data = response.json()
    print_info(f"Connected: {data.get('connected')}")
    print_info(f"Tools: {len(data.get('tools', []))}")
    assert data.get("connected") == True, "Not connected"

test.test("Connection Status Check", test_connection_status)

# ============================================================================
# TEST 9: Chat - Simple Query (Tests Tool Calling)
# ============================================================================
def test_chat_query():
    print_info("Sending test query to LLM...")
    print_info("Query: 'What tables are in the database?'")
    
    response = test.session.post(
        f"{API_BASE}/chat",
        json={"message": "What tables are in the database?"}
    )
    
    assert response.status_code == 200, f"Chat failed: {response.text}"
    data = response.json()
    
    response_text = data.get("response", "")
    tool_calls = data.get("tool_calls", [])
    
    print_info(f"Response length: {len(response_text)} chars")
    print_info(f"Tool calls made: {len(tool_calls)}")
    
    if len(response_text) > 100:
        print_info(f"Response preview: {response_text[:100]}...")
    else:
        print_info(f"Response: {response_text}")
    
    for tool_call in tool_calls:
        print_info(f"  Tool used: {tool_call.get('tool_name')}")
    
    assert len(response_text) > 0, "Empty response from LLM"
    assert len(tool_calls) > 0, "No tool calls made (LLM should call list_tables)"

test.test("Chat - Simple Database Query", test_chat_query)

# ============================================================================
# TEST 10: Get Chat History
# ============================================================================
def test_chat_history():
    print_info("Fetching chat history...")
    response = test.session.get(f"{API_BASE}/history?limit=10")
    assert response.status_code == 200, "History fetch failed"
    data = response.json()
    messages = data.get("messages", [])
    print_info(f"History messages: {len(messages)}")
    
    for msg in messages[-2:]:  # Show last 2 messages
        print_info(f"  {msg.get('role')}: {msg.get('content', '')[:50]}...")
    
    assert len(messages) > 0, "No history messages found"

test.test("Chat History Retrieval", test_chat_history)

# ============================================================================
# TEST 11: Clear Chat History
# ============================================================================
def test_clear_history():
    print_info("Clearing chat history...")
    response = test.session.post(f"{API_BASE}/clear")
    assert response.status_code == 200, "Clear history failed"
    data = response.json()
    print_info(f"Status: {data.get('status')}")
    assert data.get("status") == "cleared", "History not cleared"

test.test("Clear Chat History", test_clear_history)

# ============================================================================
# TEST 12: List Databases
# ============================================================================
def test_list_databases():
    print_info("Listing uploaded databases...")
    response = test.session.get(f"{API_BASE}/databases")
    assert response.status_code == 200, "Database list failed"
    data = response.json()
    databases = data.get("databases", [])
    print_info(f"Uploaded databases: {len(databases)}")
    
    for db in databases[:3]:  # Show first 3
        print_info(f"  Database: {db.get('name')}")
        print_info(f"    Tables: {len(db.get('tables', []))}")

test.test("List Databases", test_list_databases)

# ============================================================================
# TEST 13: Disconnect from MCP Server
# ============================================================================
def test_disconnect():
    print_info("Disconnecting from MCP server...")
    response = test.session.post(f"{API_BASE}/disconnect")
    assert response.status_code == 200, "Disconnect failed"
    data = response.json()
    print_info(f"Status: {data.get('status')}")
    assert data.get("status") in ["disconnected", "not_connected"], "Disconnect status incorrect"

test.test("Disconnect from MCP Server", test_disconnect)

# ============================================================================
# TEST 14: Verify Disconnection
# ============================================================================
def test_verify_disconnect():
    print_info("Verifying disconnection...")
    response = test.session.get(f"{API_BASE}/status")
    assert response.status_code == 200, "Status check failed"
    data = response.json()
    print_info(f"Connected: {data.get('connected')}")
    assert data.get("connected") == False, "Still connected after disconnect"

test.test("Verify Disconnection", test_verify_disconnect)

# ============================================================================
# TEST 15: Signout
# ============================================================================
def test_signout():
    print_info("Signing out...")
    response = test.session.post(f"{API_BASE}/auth/signout")
    assert response.status_code == 200, "Signout failed"
    data = response.json()
    print_info(f"Status: {data.get('status')}")
    assert data.get("status") == "signed_out", "Signout status incorrect"

test.test("Auth - Signout", test_signout)

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n")
test.summary()

# Exit with appropriate code
sys.exit(0 if test.failed == 0 else 1)
