# 🚀 Data Pipeline Quick Start Guide

## Overview
This guide will help you implement the CSV/Excel to SQLite pipeline in the correct order.

---

## Implementation Order (6 Steps)

### ✅ **Step 1: Install Dependencies (5 minutes)**

```bash
# Install required packages
pip install pandas==2.1.3 openpyxl==3.1.2 xlrd==2.0.1 python-multipart==0.0.6
```

Or update `requirements.txt` and run:
```bash
pip install -r requirements.txt
```

---

### ✅ **Step 2: Create Data Pipeline Module (1-2 hours)**

Create `data_pipeline.py` in your project root:

**Minimal viable implementation:**

```python
import pandas as pd
import sqlite3
import json
import uuid
import re
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

SQL_RESERVED_WORDS = {'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'TABLE', 'INDEX'}

class DataPipeline:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.db_dir = self.upload_dir / "databases"
        self.original_dir = self.upload_dir / "original_files"
        self.metadata_file = self.upload_dir / "metadata.json"
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Create required directories"""
        self.upload_dir.mkdir(exist_ok=True)
        self.db_dir.mkdir(exist_ok=True)
        self.original_dir.mkdir(exist_ok=True)
        
    def sanitize_column_name(self, name: str) -> str:
        """Clean column names for SQL"""
        name = name.strip()
        name = re.sub(r'[^\w]', '_', name)
        name = re.sub(r'_+', '_', name)
        name = name.strip('_')
        if name and name[0].isdigit():
            name = 'col_' + name
        if not name or name.upper() in SQL_RESERVED_WORDS:
            name = 'column_' + name
        return name.lower()
        
    async def process_upload(self, file_path: Path, original_filename: str) -> Dict[str, Any]:
        """Main entry point for file processing"""
        file_ext = file_path.suffix.lower()
        db_id = str(uuid.uuid4())
        db_name = f"{db_id}"
        
        try:
            if file_ext == '.csv':
                result = await self.convert_csv_to_sqlite(file_path, db_name)
            elif file_ext in ['.xlsx', '.xls']:
                result = await self.convert_excel_to_sqlite(file_path, db_name)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
            
            # Store metadata
            metadata = {
                "id": db_id,
                "name": f"{Path(original_filename).stem}.db",
                "original_file": original_filename,
                "db_path": str(result["db_path"]),
                "tables": result.get("tables", [{"name": "data", "row_count": result.get("row_count", 0)}]),
                "size_bytes": Path(result["db_path"]).stat().st_size,
                "uploaded_at": datetime.utcnow().isoformat() + "Z",
                "is_active": False
            }
            
            self._save_metadata(metadata)
            
            return {
                "database_id": db_id,
                "database_name": metadata["name"],
                **result
            }
            
        except Exception as e:
            logger.error(f"Upload processing failed: {e}")
            raise
            
    async def convert_csv_to_sqlite(self, csv_path: Path, db_name: str) -> Dict:
        """Convert CSV to SQLite"""
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        
        if df.empty:
            raise ValueError("CSV file is empty")
            
        df.columns = [self.sanitize_column_name(col) for col in df.columns]
        
        db_path = self.db_dir / f"{db_name}.db"
        
        with sqlite3.connect(db_path) as conn:
            df.to_sql('data', conn, if_exists='replace', index=False)
            
        return {
            "success": True,
            "db_path": str(db_path),
            "table_name": "data",
            "row_count": len(df),
            "column_count": len(df.columns)
        }
        
    async def convert_excel_to_sqlite(self, excel_path: Path, db_name: str) -> Dict:
        """Convert Excel (all sheets) to SQLite"""
        excel_file = pd.ExcelFile(excel_path)
        sheet_names = excel_file.sheet_names
        
        if not sheet_names:
            raise ValueError("Excel file has no sheets")
            
        db_path = self.db_dir / f"{db_name}.db"
        tables_info = []
        
        with sqlite3.connect(db_path) as conn:
            for sheet_name in sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                table_name = self.sanitize_column_name(sheet_name)
                df.columns = [self.sanitize_column_name(col) for col in df.columns]
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                
                tables_info.append({
                    "name": table_name,
                    "row_count": len(df),
                    "column_count": len(df.columns)
                })
        
        return {
            "success": True,
            "db_path": str(db_path),
            "tables": tables_info,
            "total_rows": sum(t["row_count"] for t in tables_info)
        }
        
    def _save_metadata(self, new_metadata: Dict):
        """Save database metadata"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
        else:
            data = {"databases": [], "active_database_id": None}
            
        data["databases"].append(new_metadata)
        
        with open(self.metadata_file, 'w') as f:
            json.dump(data, f, indent=2)
            
    def list_databases(self) -> Dict:
        """List all uploaded databases"""
        if not self.metadata_file.exists():
            return {"databases": []}
            
        with open(self.metadata_file, 'r') as f:
            return json.load(f)
            
    def get_database_by_id(self, db_id: str) -> Dict:
        """Get database metadata by ID"""
        data = self.list_databases()
        for db in data.get("databases", []):
            if db["id"] == db_id:
                return db
        raise ValueError(f"Database not found: {db_id}")
```

---

### ✅ **Step 3: Add FastAPI Endpoints (30-45 minutes)**

Add these imports to `fastapi_app_fixed.py`:
```python
from fastapi import UploadFile, File
from data_pipeline import DataPipeline
import shutil
```

Add this after the global variables:
```python
# Initialize pipeline
pipeline = DataPipeline()
```

Add these new endpoints:

```python
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and convert CSV/Excel file to SQLite"""
    
    # Validate file type
    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")
    
    # Validate file size (100MB max)
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    
    max_size = 100 * 1024 * 1024
    if size > max_size:
        raise HTTPException(status_code=400, detail=f"File too large (max 100MB)")
    
    try:
        # Save uploaded file temporarily
        temp_path = pipeline.original_dir / f"temp_{uuid.uuid4()}{file_ext}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process file
        result = await pipeline.process_upload(temp_path, file.filename)
        
        # Move to permanent location
        final_path = pipeline.original_dir / f"{result['database_id']}{file_ext}"
        temp_path.rename(final_path)
        
        logger.info(f"File uploaded and converted: {file.filename}")
        
        return {
            "status": "success",
            "message": "File uploaded and converted successfully",
            **result
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/databases")
async def list_databases():
    """List all uploaded databases"""
    return pipeline.list_databases()


@app.post("/api/switch-database")
async def switch_database(request: dict):
    """Switch to a different database"""
    global current_client, current_agent, current_streaming_agent
    
    database_id = request.get("database_id")
    if not database_id:
        raise HTTPException(status_code=400, detail="database_id required")
    
    try:
        db_metadata = pipeline.get_database_by_id(database_id)
        db_path = db_metadata["db_path"]
        
        async with client_lock:
            # Disconnect current client
            if current_client:
                try:
                    await current_client.close()
                except:
                    pass
            
            # Create new server config for this database
            server_config = MCPServerConfig(
                name="SQLite",
                command="python",
                args=["sqlite_mcp_fastmcp.py", db_path]
            )
            
            # Connect to new database
            client = MCPClient(server_config)
            await client.connect()
            
            # Get current model
            current_model = current_agent.model if current_agent else "z-ai/glm-4.5-air:free"
            
            # Create new agents
            agent = LLMAgent(client, model=current_model)
            streaming_agent = StreamingLLMAgent(client, model=current_model)
            
            current_client = client
            current_agent = agent
            current_streaming_agent = streaming_agent
            
            # Update metadata
            data = pipeline.list_databases()
            for db in data["databases"]:
                db["is_active"] = (db["id"] == database_id)
            data["active_database_id"] = database_id
            
            with open(pipeline.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Switched to database: {db_metadata['name']}")
            
            return {
                "status": "success",
                "database_name": db_metadata["name"],
                "database_id": database_id
            }
            
    except Exception as e:
        logger.error(f"Database switch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/database/{database_id}/info")
async def get_database_info(database_id: str):
    """Get detailed database information"""
    try:
        db_metadata = pipeline.get_database_by_id(database_id)
        db_path = Path(db_metadata["db_path"])
        
        # Get table details from SQLite
        import aiosqlite
        
        tables_info = []
        async with aiosqlite.connect(db_path) as db:
            for table_meta in db_metadata.get("tables", []):
                table_name = table_meta["name"]
                
                # Get column info
                cursor = await db.execute(f"PRAGMA table_info({table_name})")
                columns_raw = await cursor.fetchall()
                
                columns = [
                    {
                        "name": col[1],
                        "type": col[2],
                        "nullable": not bool(col[3]),
                        "primary_key": bool(col[5])
                    }
                    for col in columns_raw
                ]
                
                # Get row count
                cursor = await db.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = (await cursor.fetchone())[0]
                
                tables_info.append({
                    "name": table_name,
                    "row_count": row_count,
                    "columns": columns
                })
        
        return {
            "id": database_id,
            "name": db_metadata["name"],
            "tables": tables_info
        }
        
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/database/{database_id}")
async def delete_database(database_id: str):
    """Delete an uploaded database"""
    try:
        db_metadata = pipeline.get_database_by_id(database_id)
        
        # Delete database file
        db_path = Path(db_metadata["db_path"])
        if db_path.exists():
            db_path.unlink()
        
        # Delete original file
        for ext in ['.csv', '.xlsx', '.xls']:
            original_path = pipeline.original_dir / f"{database_id}{ext}"
            if original_path.exists():
                original_path.unlink()
        
        # Remove from metadata
        data = pipeline.list_databases()
        data["databases"] = [db for db in data["databases"] if db["id"] != database_id]
        
        if data["active_database_id"] == database_id:
            data["active_database_id"] = None
        
        with open(pipeline.metadata_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return {"status": "success", "message": "Database deleted"}
        
    except Exception as e:
        logger.error(f"Failed to delete database: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

Add this import at the top:
```python
import uuid
```

---

### ✅ **Step 4: Update UI (1-2 hours)**

Add to `static/index.html` in the `<style>` section:

```css
.upload-section {
    background: white;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
}
.upload-zone {
    border: 2px dashed #cbd5e1;
    border-radius: 8px;
    padding: 30px;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s;
}
.upload-zone:hover {
    border-color: #667eea;
    background: #f8fafc;
}
.upload-zone.dragover {
    border-color: #667eea;
    background: #eef2ff;
}
.upload-icon {
    font-size: 48px;
}
#uploadProgress {
    margin-top: 10px;
}
.progress-bar {
    height: 4px;
    background: linear-gradient(90deg, #667eea, #764ba2);
    border-radius: 2px;
    animation: progress 1.5s infinite;
}
@keyframes progress {
    0% { width: 0%; }
    100% { width: 100%; }
}
.database-info {
    background: white;
    padding: 15px;
    border-radius: 8px;
    margin-top: 15px;
    font-size: 13px;
}
.button-icon {
    padding: 12px !important;
    width: auto !important;
    margin-left: 5px !important;
}
```

Add in the sidebar section (before the tools list):

```html
<!-- File Upload Section -->
<div class="upload-section">
    <h3>📁 Upload Data</h3>
    <div class="upload-zone" id="uploadZone">
        <input type="file" id="fileInput" accept=".csv,.xlsx,.xls" hidden>
        <div class="upload-content">
            <span class="upload-icon">📤</span>
            <p>Drop CSV/Excel here</p>
            <button onclick="document.getElementById('fileInput').click()" type="button">
                Browse
            </button>
            <br><small>Max 100MB</small>
        </div>
    </div>
    <div id="uploadProgress" style="display: none;">
        <div class="progress-bar"></div>
        <span class="progress-text">Uploading...</span>
    </div>
</div>

<!-- Database Selector -->
<div class="control-group">
    <label>Database:</label>
    <div style="display: flex; gap: 5px;">
        <select id="databaseSelect" style="flex: 1;" onchange="switchDatabase()">
            <option value="">Select database...</option>
        </select>
        <button onclick="refreshDatabases()" class="button-icon" type="button" title="Refresh">🔄</button>
    </div>
</div>

<div class="database-info" id="dbInfo" style="display: none;">
    <h4>📊 Database Info</h4>
    <div id="dbDetails"></div>
</div>
```

Add in the `<script>` section:

```javascript
// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    setupFileUpload();
    refreshDatabases();
});

function setupFileUpload() {
    const zone = document.getElementById('uploadZone');
    const input = document.getElementById('fileInput');
    
    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });
    
    zone.addEventListener('dragleave', () => {
        zone.classList.remove('dragover');
    });
    
    zone.addEventListener('drop', async (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            await uploadFile(e.dataTransfer.files[0]);
        }
    });
    
    input.addEventListener('change', async (e) => {
        if (e.target.files.length > 0) {
            await uploadFile(e.target.files[0]);
        }
    });
}

async function uploadFile(file) {
    const validTypes = ['text/csv', 'application/vnd.ms-excel', 
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
    if (!validTypes.includes(file.type) && !file.name.match(/\.(csv|xlsx|xls)$/i)) {
        alert('Invalid file type. Please upload CSV or Excel file.');
        return;
    }
    
    if (file.size > 100 * 1024 * 1024) {
        alert('File too large. Maximum size is 100MB.');
        return;
    }
    
    const progressDiv = document.getElementById('uploadProgress');
    progressDiv.style.display = 'block';
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(`Success! Database created with ${data.row_count || data.total_rows} rows`);
            await refreshDatabases();
            if (data.database_id) {
                await switchToDatabase(data.database_id);
            }
        } else {
            alert('Upload failed: ' + data.detail);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        progressDiv.style.display = 'none';
        document.getElementById('fileInput').value = '';
    }
}

async function refreshDatabases() {
    try {
        const response = await fetch('/api/databases');
        const data = await response.json();
        
        const select = document.getElementById('databaseSelect');
        select.innerHTML = '<option value="">Select database...</option>';
        
        (data.databases || []).forEach(db => {
            const option = document.createElement('option');
            option.value = db.id;
            option.textContent = `${db.name} (${db.tables ? db.tables.length : 0} tables)`;
            if (db.is_active) option.selected = true;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to refresh databases:', error);
    }
}

async function switchDatabase() {
    const select = document.getElementById('databaseSelect');
    const dbId = select.value;
    if (!dbId) return;
    await switchToDatabase(dbId);
}

async function switchToDatabase(dbId) {
    try {
        const response = await fetch('/api/switch-database', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ database_id: dbId })
        });
        
        if (response.ok) {
            const data = await response.json();
            alert(`Switched to ${data.database_name}`);
            await loadDatabaseInfo(dbId);
            
            // Update connection status
            connected = true;
            document.getElementById('statusBadge').textContent = 'Connected';
            document.getElementById('statusBadge').className = 'status-badge status-connected';
            document.getElementById('messageInput').disabled = false;
            document.getElementById('sendBtn').disabled = false;
        } else {
            const data = await response.json();
            alert('Failed to switch database: ' + data.detail);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function loadDatabaseInfo(dbId) {
    try {
        const response = await fetch(`/api/database/${dbId}/info`);
        const data = await response.json();
        
        const infoDiv = document.getElementById('dbInfo');
        const detailsDiv = document.getElementById('dbDetails');
        
        let html = '<ul style="margin: 0; padding-left: 20px;">';
        data.tables.forEach(table => {
            html += `<li><strong>${table.name}</strong>: ${table.row_count} rows, ${table.columns.length} cols</li>`;
        });
        html += '</ul>';
        
        detailsDiv.innerHTML = html;
        infoDiv.style.display = 'block';
    } catch (error) {
        console.error('Failed to load database info:', error);
    }
}
```

---

### ✅ **Step 5: Test the Pipeline (30 minutes)**

1. **Start the server:**
```bash
python run_fixed.py
```

2. **Test with a CSV file:**
   - Create a simple test CSV:
   ```csv
   Name,Age,City
   John,30,New York
   Jane,25,Boston
   Bob,35,Chicago
   ```
   - Save as `test_data.csv`
   - Upload via UI
   - Ask: "Show me all the data"

3. **Test with Excel file:**
   - Create a simple Excel with 2 sheets
   - Upload and query both sheets

---

### ✅ **Step 6: Create Example Data (15 minutes)**

Create `examples/` folder with sample files:

**`examples/sales_data.csv`:**
```csv
Date,Product,Quantity,Price,Total
2024-01-01,Widget A,10,29.99,299.90
2024-01-02,Widget B,5,49.99,249.95
2024-01-03,Widget A,8,29.99,239.92
```

**`examples/README.md`:**
```markdown
# Example Data Files

Upload these files to test the data pipeline:

1. **sales_data.csv** - Simple sales data
2. **financial_report.xlsx** - Multi-sheet financial data

## Test Queries

After uploading `sales_data.csv`, try:
- "What's the total revenue?"
- "Which product sold the most?"
- "Show me sales on 2024-01-02"
```

---

## 🎉 Success Checklist

- [ ] Dependencies installed
- [ ] `data_pipeline.py` created
- [ ] FastAPI endpoints added
- [ ] UI updated with upload functionality
- [ ] Can upload CSV file
- [ ] Can upload Excel file
- [ ] Can switch between databases
- [ ] Can query uploaded data with AI
- [ ] Database info displays correctly

---

## 🐛 Troubleshooting

**Issue:** `ModuleNotFoundError: No module named 'pandas'`
- **Fix:** `pip install pandas openpyxl xlrd python-multipart`

**Issue:** Upload button doesn't work
- **Fix:** Check browser console for errors, ensure `setupFileUpload()` is called

**Issue:** Database switch fails
- **Fix:** Check that `sqlite_mcp_fastmcp.py` accepts database path as argument

**Issue:** Can't query uploaded data
- **Fix:** Verify database file exists in `uploads/databases/` folder

---

## 📞 Need Help?

Review the full implementation plan in `DATA_PIPELINE_PLAN.md` for:
- Detailed code examples
- Best practices
- Security considerations
- Performance optimization tips

---

**Ready to implement? Start with Step 1!** 🚀
