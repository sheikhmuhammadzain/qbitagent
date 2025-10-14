"""
SQLite MCP Server using FastMCP
Provides CRUD operations for SQLite database following MCP protocol
Based on: https://felix-pappe.medium.com/
"""
from mcp.server.fastmcp import FastMCP
import aiosqlite
import anyio
import sys
from pathlib import Path

# Initialize FastMCP server
mcp = FastMCP("sqlite-crud")

# Database file path (from command line or default)
DB_FILE = sys.argv[1] if len(sys.argv) > 1 else "example.db"


async def init_db():
    """Initialize the SQLite database with required tables"""
    async with aiosqlite.connect(DB_FILE) as db:
        # Create users table if it doesn't exist
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create products table if it doesn't exist
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL,
                quantity INTEGER DEFAULT 0
            )
        """)
        
        await db.commit()
        print(f"Database initialized: {Path(DB_FILE).resolve()}", file=sys.stderr)


@mcp.tool()
async def list_tables() -> list[str]:
    """List all tables in the SQLite database"""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        rows = await cursor.fetchall()
    return [row[0] for row in rows]


@mcp.tool()
async def describe_table(table_name: str) -> list[dict]:
    """
    Get the schema/structure of a specific table
    
    Args:
        table_name: Name of the table to describe
    """
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(f"PRAGMA table_info({table_name})")
        rows = await cursor.fetchall()
    
    return [
        {
            "column_id": row[0],
            "name": row[1],
            "type": row[2],
            "not_null": bool(row[3]),
            "default_value": row[4],
            "primary_key": bool(row[5])
        }
        for row in rows
    ]


@mcp.tool()
async def execute_query(query: str) -> str:
    """
    Execute a SQL query (SELECT, INSERT, UPDATE, DELETE)
    
    Args:
        query: The SQL query to execute
    
    Returns:
        JSON string with query results or status message
    """
    import json
    
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.cursor()
        
        try:
            await cursor.execute(query)
            
            # Check if it's a SELECT query
            if query.strip().upper().startswith(('SELECT', 'PRAGMA', 'EXPLAIN')):
                rows = await cursor.fetchall()
                results = [dict(row) for row in rows]
                return json.dumps(results, indent=2, default=str)
            else:
                # For INSERT, UPDATE, DELETE
                await db.commit()
                return json.dumps({
                    "status": "success",
                    "affected_rows": cursor.rowcount,
                    "message": "Query executed successfully"
                }, indent=2)
                
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            }, indent=2)


# Add a simple render_chart tool that returns a chart spec for the frontend
@mcp.tool()
def render_chart(query: str, x: str, y: str, chart: str = "bar") -> dict:
    """Return a charting spec from a SQL query.
    Args:
      query: SQL SELECT that returns at least columns x and y
      x: name of the x axis column
      y: name of the y axis column
      chart: one of 'bar' | 'line' | 'area' | 'pie'
    Returns: { "type": "chart", "spec": { ... }} for the frontend to render.
    """
    import sqlite3
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    data = [{k: row[k] for k in row.keys()} for row in rows]
    return {
        "type": "chart",
        "spec": {
            "chart": chart,
            "x": x,
            "y": y,
            "data": data,
        },
    }


@mcp.tool()
async def get_database_info() -> str:
    """Get information about the database (file size, tables, SQLite version)"""
    import json
    
    info = {}
    
    # File information
    db_path = Path(DB_FILE)
    if db_path.exists():
        stat = db_path.stat()
        info["database_file"] = str(db_path.resolve())
        info["file_size_bytes"] = stat.st_size
        info["file_size_readable"] = f"{stat.st_size:,} bytes"
    else:
        info["database_file"] = "Not found"
    
    async with aiosqlite.connect(DB_FILE) as db:
        # Get SQLite version
        cursor = await db.execute("SELECT sqlite_version()")
        version = await cursor.fetchone()
        info["sqlite_version"] = version[0]
        
        # Get table count
        cursor = await db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        )
        count = await cursor.fetchone()
        info["table_count"] = count[0]
        
        # Get table names
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = await cursor.fetchall()
        info["tables"] = [table[0] for table in tables]
    
    return json.dumps(info, indent=2)


@mcp.tool()
async def create_user(name: str, email: str = None) -> str:
    """
    Create a new user in the database
    
    Args:
        name: User's name (required)
        email: User's email address (optional)
    """
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            (name, email)
        )
        await db.commit()
        return f"User created with ID: {cursor.lastrowid}"


@mcp.tool()
async def list_users() -> str:
    """List all users from the database"""
    import json
    
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users ORDER BY id")
        rows = await cursor.fetchall()
    
    users = [dict(row) for row in rows]
    return json.dumps(users, indent=2, default=str)


@mcp.tool()
async def update_user(user_id: int, name: str = None, email: str = None) -> str:
    """
    Update a user's information
    
    Args:
        user_id: ID of the user to update
        name: New name (optional)
        email: New email (optional)
    """
    if not name and not email:
        return "Error: At least one field (name or email) must be provided"
    
    updates = []
    params = []
    
    if name:
        updates.append("name = ?")
        params.append(name)
    if email:
        updates.append("email = ?")
        params.append(email)
    
    params.append(user_id)
    
    async with aiosqlite.connect(DB_FILE) as db:
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        cursor = await db.execute(query, params)
        await db.commit()
        
        if cursor.rowcount > 0:
            return f"User {user_id} updated successfully"
        else:
            return f"No user found with ID {user_id}"


@mcp.tool()
async def delete_user(user_id: int) -> str:
    """
    Delete a user from the database
    
    Args:
        user_id: ID of the user to delete
    """
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await db.commit()
        
        if cursor.rowcount > 0:
            return f"User {user_id} deleted successfully"
        else:
            return f"No user found with ID {user_id}"


async def run():
    """Main entry point - initialize database and start MCP server"""
    print(f"Starting SQLite MCP Server...", file=sys.stderr)
    print(f"Database: {Path(DB_FILE).resolve()}", file=sys.stderr)
    
    # Initialize database tables
    await init_db()
    
    # Start MCP server using stdio transport
    print("Server ready and listening on stdio", file=sys.stderr)
    await mcp.run_stdio_async()


if __name__ == "__main__":
    anyio.run(run)
