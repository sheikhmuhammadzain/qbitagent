# 📊 CSV/Excel to SQLite Data Pipeline - Implementation Plan

## 🎯 Overview

This document outlines the complete implementation plan for a data pipeline that allows users to:
1. Upload CSV or Excel files via the web UI
2. Automatically convert files to SQLite databases
3. Query the data intelligently using AI-powered tool calling
4. Switch between multiple uploaded databases seamlessly

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Web UI (React-like)                   │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ File Upload     │  │ Database     │  │ Query          │ │
│  │ - Drag & Drop   │  │ Selector     │  │ Interface      │ │
│  │ - Browse Button │  │ - List DBs   │  │ - Chat with AI │ │
│  └─────────────────┘  └──────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ New Endpoints:                                        │   │
│  │ - POST /api/upload           (Upload file)           │   │
│  │ - GET  /api/databases        (List databases)        │   │
│  │ - POST /api/switch-database  (Change active DB)      │   │
│  │ - DELETE /api/database/{id}  (Delete database)       │   │
│  │ - GET  /api/database/{id}/info (Get DB metadata)     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Data Pipeline Module                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Functions:                                            │   │
│  │ - validate_file()         (Check format & size)      │   │
│  │ - infer_schema()          (Auto-detect data types)   │   │
│  │ - convert_to_sqlite()     (Create DB from file)      │   │
│  │ - sanitize_table_name()   (Clean column names)       │   │
│  │ - get_database_metadata() (Extract DB info)          │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│            Enhanced SQLite MCP Server                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Features:                                             │   │
│  │ - Dynamic database switching                         │   │
│  │ - Multi-sheet Excel support                          │   │
│  │ - Automatic schema detection                         │   │
│  │ - Query optimization hints                           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 SQLite Database Files                        │
│  uploads/                                                    │
│  ├── original_files/      (CSV/Excel source files)          │
│  ├── databases/           (Converted SQLite .db files)       │
│  └── metadata.json        (Database registry & info)         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Implementation Steps

### **Step 1: Create Data Pipeline Module**

Create `data_pipeline.py` with the following components:

#### **Best Practices:**
- ✅ Use pandas for robust data handling
- ✅ Implement strict file validation (size, format, content)
- ✅ Auto-detect and convert data types intelligently
- ✅ Sanitize column names (remove special chars, spaces)
- ✅ Handle missing values appropriately
- ✅ Support multiple sheets in Excel files
- ✅ Create indexes on primary key columns
- ✅ Store metadata for each database

#### **Key Functions:**

```python
class DataPipeline:
    """Handle CSV/Excel to SQLite conversion"""
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.db_dir = self.upload_dir / "databases"
        self.original_dir = self.upload_dir / "original_files"
        self.metadata_file = self.upload_dir / "metadata.json"
        self._ensure_directories()
    
    async def validate_file(self, file, max_size_mb: int = 100) -> Dict:
        """Validate uploaded file format and size"""
        
    async def convert_csv_to_sqlite(self, csv_path: Path, db_name: str) -> Dict:
        """Convert CSV file to SQLite database"""
        
    async def convert_excel_to_sqlite(self, excel_path: Path, db_name: str) -> Dict:
        """Convert Excel file (all sheets) to SQLite database"""
        
    def infer_schema(self, df: pd.DataFrame) -> Dict:
        """Intelligently infer column types and constraints"""
        
    def sanitize_column_name(self, name: str) -> str:
        """Clean column names for SQL compatibility"""
        
    def get_database_info(self, db_path: Path) -> Dict:
        """Extract metadata from SQLite database"""
```

---

### **Step 2: Add FastAPI Upload Endpoints**

Update `fastapi_app_fixed.py`:

#### **New Endpoints:**

```python
from fastapi import UploadFile, File
from data_pipeline import DataPipeline

# Initialize pipeline
pipeline = DataPipeline()

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload CSV or Excel file and convert to SQLite
    
    Response:
    {
        "status": "success",
        "database_id": "uuid",
        "database_name": "uploaded_data.db",
        "tables": ["sheet1", "sheet2"],
        "row_count": 1000,
        "message": "File uploaded and converted successfully"
    }
    """

@app.get("/api/databases")
async def list_databases():
    """
    List all uploaded databases
    
    Response:
    {
        "databases": [
            {
                "id": "uuid",
                "name": "sales_data.db",
                "original_file": "sales.csv",
                "tables": ["sales"],
                "size_bytes": 524288,
                "uploaded_at": "2025-10-11T10:30:00Z",
                "is_active": true
            }
        ]
    }
    """

@app.post("/api/switch-database")
async def switch_database(database_id: str):
    """
    Switch to a different uploaded database
    Reconnects MCP client to new database
    """

@app.delete("/api/database/{database_id}")
async def delete_database(database_id: str):
    """Delete an uploaded database and its files"""

@app.get("/api/database/{database_id}/info")
async def get_database_info(database_id: str):
    """
    Get detailed information about a database
    
    Response:
    {
        "id": "uuid",
        "name": "data.db",
        "tables": [
            {
                "name": "sales",
                "row_count": 1500,
                "columns": [
                    {"name": "id", "type": "INTEGER", "primary_key": true},
                    {"name": "date", "type": "TEXT"},
                    {"name": "amount", "type": "REAL"}
                ]
            }
        ]
    }
    """
```

---

### **Step 3: Update SQLite MCP Server**

Modify `sqlite_mcp_fastmcp.py` to support dynamic database switching:

#### **Enhancements:**

```python
class DynamicSQLiteMCP:
    """Enhanced SQLite MCP with dynamic database support"""
    
    def __init__(self):
        self.current_db_path = None
        self.mcp = FastMCP("sqlite-dynamic")
        self._register_tools()
    
    def set_database(self, db_path: str):
        """Switch to a different database"""
        self.current_db_path = db_path
        
    @mcp.tool()
    async def list_tables() -> list[str]:
        """List all tables in current database"""
        
    @mcp.tool()
    async def get_table_summary(table_name: str) -> str:
        """
        Get summary statistics for a table
        Returns: row count, column info, sample data
        """
    
    @mcp.tool()
    async def analyze_data(table_name: str, analysis_type: str) -> str:
        """
        Perform data analysis (basic stats, distributions, correlations)
        analysis_type: 'summary', 'describe', 'correlations', 'missing_values'
        """
```

---

### **Step 4: Enhance UI Components**

Update `static/index.html`:

#### **New UI Elements:**

```html
<!-- File Upload Section -->
<div class="upload-section">
    <h3>📁 Upload Data File</h3>
    <div class="upload-zone" id="uploadZone">
        <input type="file" id="fileInput" accept=".csv,.xlsx,.xls" hidden>
        <div class="upload-content">
            <span class="upload-icon">📤</span>
            <p>Drag & Drop CSV or Excel file here</p>
            <button onclick="document.getElementById('fileInput').click()">
                Browse Files
            </button>
            <small>Max size: 100MB | Formats: CSV, XLSX, XLS</small>
        </div>
    </div>
    <div id="uploadProgress" style="display: none;">
        <div class="progress-bar"></div>
        <span class="progress-text">Uploading...</span>
    </div>
</div>

<!-- Database Selector -->
<div class="control-group">
    <label>Active Database:</label>
    <select id="databaseSelect" onchange="switchDatabase()">
        <option value="">Select a database...</option>
    </select>
    <button onclick="refreshDatabases()" class="button-icon">🔄</button>
    <button onclick="deleteDatabaseConfirm()" class="button-icon">🗑️</button>
</div>

<!-- Database Info Panel -->
<div class="database-info" id="dbInfo" style="display: none;">
    <h4>📊 Database Info</h4>
    <div id="dbDetails"></div>
</div>
```

#### **JavaScript Functions:**

```javascript
// File upload with drag & drop
function setupFileUpload() {
    const zone = document.getElementById('uploadZone');
    const input = document.getElementById('fileInput');
    
    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });
    
    zone.addEventListener('drop', async (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            await uploadFile(files[0]);
        }
    });
    
    input.addEventListener('change', async (e) => {
        if (e.target.files.length > 0) {
            await uploadFile(e.target.files[0]);
        }
    });
}

async function uploadFile(file) {
    // Validate file
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
    
    // Show progress
    const progressDiv = document.getElementById('uploadProgress');
    progressDiv.style.display = 'block';
    
    // Upload file
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(`Success! Database created with ${data.row_count} rows`);
            await refreshDatabases();
            await switchDatabase(data.database_id);
        } else {
            alert('Upload failed: ' + data.detail);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    } finally {
        progressDiv.style.display = 'none';
    }
}

async function refreshDatabases() {
    const response = await fetch('/api/databases');
    const data = await response.json();
    
    const select = document.getElementById('databaseSelect');
    select.innerHTML = '<option value="">Select a database...</option>';
    
    data.databases.forEach(db => {
        const option = document.createElement('option');
        option.value = db.id;
        option.textContent = `${db.name} (${db.tables.length} tables)`;
        if (db.is_active) option.selected = true;
        select.appendChild(option);
    });
}

async function switchDatabase(dbId) {
    if (!dbId) return;
    
    const response = await fetch('/api/switch-database', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ database_id: dbId })
    });
    
    if (response.ok) {
        const data = await response.json();
        alert(`Switched to ${data.database_name}`);
        await loadDatabaseInfo(dbId);
    }
}

async function loadDatabaseInfo(dbId) {
    const response = await fetch(`/api/database/${dbId}/info`);
    const data = await response.json();
    
    const infoDiv = document.getElementById('dbInfo');
    const detailsDiv = document.getElementById('dbDetails');
    
    let html = '<ul>';
    data.tables.forEach(table => {
        html += `<li><strong>${table.name}</strong>: ${table.row_count} rows, ${table.columns.length} columns</li>`;
    });
    html += '</ul>';
    
    detailsDiv.innerHTML = html;
    infoDiv.style.display = 'block';
}
```

---

### **Step 5: Database Metadata Management**

Create `metadata.json` structure:

```json
{
    "databases": [
        {
            "id": "uuid-1234",
            "name": "sales_data.db",
            "original_file": "sales_2024.csv",
            "db_path": "uploads/databases/sales_data.db",
            "tables": [
                {
                    "name": "sales_2024",
                    "row_count": 5000,
                    "column_count": 12,
                    "columns": [
                        {"name": "id", "type": "INTEGER", "nullable": false},
                        {"name": "date", "type": "TEXT"},
                        {"name": "amount", "type": "REAL"}
                    ]
                }
            ],
            "size_bytes": 1048576,
            "uploaded_at": "2025-10-11T10:30:00Z",
            "is_active": true
        }
    ],
    "active_database_id": "uuid-1234"
}
```

---

## 🔧 Best Practices Implementation

### **1. File Validation**
```python
def validate_file(self, file: UploadFile) -> Dict:
    """Comprehensive file validation"""
    
    # Check extension
    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise ValueError(f"Unsupported file type: {file_ext}")
    
    # Check MIME type
    valid_mimes = ['text/csv', 'application/vnd.ms-excel', 
                   'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
    if file.content_type not in valid_mimes:
        raise ValueError(f"Invalid MIME type: {file.content_type}")
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    size = file.file.tell()
    file.file.seek(0)  # Reset
    
    max_size = 100 * 1024 * 1024  # 100MB
    if size > max_size:
        raise ValueError(f"File too large: {size} bytes (max: {max_size})")
    
    return {"valid": True, "size": size, "extension": file_ext}
```

### **2. Smart Schema Inference**
```python
def infer_schema(self, df: pd.DataFrame) -> Dict[str, str]:
    """Intelligently infer SQL types from pandas DataFrame"""
    
    type_mapping = {}
    
    for col in df.columns:
        # Get pandas dtype
        dtype = df[col].dtype
        
        # Infer SQL type
        if pd.api.types.is_integer_dtype(dtype):
            type_mapping[col] = "INTEGER"
        elif pd.api.types.is_float_dtype(dtype):
            type_mapping[col] = "REAL"
        elif pd.api.types.is_bool_dtype(dtype):
            type_mapping[col] = "INTEGER"  # SQLite doesn't have BOOLEAN
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            type_mapping[col] = "TEXT"  # Store as ISO format string
        else:
            type_mapping[col] = "TEXT"
    
    return type_mapping
```

### **3. Column Name Sanitization**
```python
def sanitize_column_name(self, name: str) -> str:
    """Make column names SQL-safe"""
    
    # Remove leading/trailing whitespace
    name = name.strip()
    
    # Replace spaces and special chars with underscores
    name = re.sub(r'[^\w]', '_', name)
    
    # Remove consecutive underscores
    name = re.sub(r'_+', '_', name)
    
    # Remove leading/trailing underscores
    name = name.strip('_')
    
    # Ensure it doesn't start with a number
    if name and name[0].isdigit():
        name = 'col_' + name
    
    # Handle empty or reserved words
    if not name or name.upper() in SQL_RESERVED_WORDS:
        name = 'column_' + name
    
    return name.lower()
```

### **4. Error Handling & Logging**
```python
import logging

logger = logging.getLogger(__name__)

async def convert_csv_to_sqlite(self, csv_path: Path, db_name: str) -> Dict:
    """Convert CSV to SQLite with comprehensive error handling"""
    
    try:
        # Read CSV with error handling
        logger.info(f"Reading CSV file: {csv_path}")
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        
        # Validate data
        if df.empty:
            raise ValueError("CSV file is empty")
        
        if len(df.columns) == 0:
            raise ValueError("CSV has no columns")
        
        # Sanitize column names
        df.columns = [self.sanitize_column_name(col) for col in df.columns]
        
        # Create database
        db_path = self.db_dir / f"{db_name}.db"
        logger.info(f"Creating SQLite database: {db_path}")
        
        # Convert to SQLite
        with sqlite3.connect(db_path) as conn:
            df.to_sql('data', conn, if_exists='replace', index=False)
            
            # Create indexes on potential key columns
            self._create_indexes(conn, 'data', df.columns)
        
        logger.info(f"Successfully converted {len(df)} rows to SQLite")
        
        return {
            "success": True,
            "db_path": str(db_path),
            "table_name": "data",
            "row_count": len(df),
            "column_count": len(df.columns)
        }
        
    except pd.errors.EmptyDataError:
        logger.error("CSV file is empty")
        raise ValueError("CSV file contains no data")
    except pd.errors.ParserError as e:
        logger.error(f"CSV parsing error: {e}")
        raise ValueError(f"Invalid CSV format: {str(e)}")
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        raise
```

### **5. Excel Multi-Sheet Support**
```python
async def convert_excel_to_sqlite(self, excel_path: Path, db_name: str) -> Dict:
    """Convert Excel file (all sheets) to SQLite"""
    
    try:
        # Read all sheets
        excel_file = pd.ExcelFile(excel_path)
        sheet_names = excel_file.sheet_names
        
        if not sheet_names:
            raise ValueError("Excel file has no sheets")
        
        db_path = self.db_dir / f"{db_name}.db"
        
        with sqlite3.connect(db_path) as conn:
            tables_info = []
            
            for sheet_name in sheet_names:
                # Read sheet
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                
                # Sanitize table name
                table_name = self.sanitize_column_name(sheet_name)
                
                # Sanitize column names
                df.columns = [self.sanitize_column_name(col) for col in df.columns]
                
                # Write to database
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                
                tables_info.append({
                    "original_name": sheet_name,
                    "table_name": table_name,
                    "row_count": len(df),
                    "column_count": len(df.columns)
                })
        
        return {
            "success": True,
            "db_path": str(db_path),
            "tables": tables_info,
            "total_rows": sum(t["row_count"] for t in tables_info)
        }
        
    except Exception as e:
        logger.error(f"Excel conversion failed: {e}")
        raise
```

---

## 📦 Dependencies

Add to `requirements.txt`:

```text
# Existing dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
mcp==0.9.0
httpx==0.25.1
python-dotenv==1.0.0
aiosqlite==0.19.0

# New dependencies for data pipeline
pandas==2.1.3              # Data manipulation
openpyxl==3.1.2           # Excel .xlsx support
xlrd==2.0.1               # Excel .xls support (older format)
python-multipart==0.0.6   # File upload support
```

---

## 🧪 Testing Strategy

### **Unit Tests**
```python
# test_data_pipeline.py

def test_validate_csv_file():
    """Test CSV file validation"""
    
def test_validate_excel_file():
    """Test Excel file validation"""
    
def test_schema_inference():
    """Test data type inference"""
    
def test_column_sanitization():
    """Test column name cleaning"""
    
def test_csv_conversion():
    """Test CSV to SQLite conversion"""
    
def test_excel_conversion():
    """Test Excel to SQLite conversion"""
    
def test_multi_sheet_excel():
    """Test multi-sheet Excel handling"""
```

### **Integration Tests**
```python
# test_api_upload.py

async def test_upload_csv_endpoint():
    """Test CSV upload via API"""
    
async def test_upload_excel_endpoint():
    """Test Excel upload via API"""
    
async def test_switch_database():
    """Test database switching"""
    
async def test_query_uploaded_data():
    """Test querying uploaded data with AI"""
```

---

## 🚀 Usage Examples

### **Example 1: Upload Sales Data**
```python
# 1. User uploads sales_2024.csv
# 2. System creates sales_2024.db with 'data' table
# 3. User asks: "What were the top 5 sales last month?"
# 4. AI uses execute_query tool to run:
#    SELECT * FROM data WHERE date >= '2024-09-01' 
#    ORDER BY amount DESC LIMIT 5
```

### **Example 2: Multi-Sheet Excel Analysis**
```python
# 1. User uploads financial_report.xlsx with sheets: 
#    - Revenue
#    - Expenses  
#    - Profit
# 2. System creates financial_report.db with 3 tables
# 3. User asks: "Compare revenue vs expenses by quarter"
# 4. AI uses multiple queries and synthesizes answer
```

---

## 🛡️ Security Considerations

1. **File Upload Security**
   - Validate file extensions and MIME types
   - Scan for malicious content
   - Limit file size (100MB default)
   - Use UUID for file names to prevent path traversal

2. **SQL Injection Prevention**
   - Use parameterized queries only
   - Sanitize all table/column names
   - Validate SQL queries before execution

3. **Resource Management**
   - Implement upload rate limiting
   - Set max concurrent uploads
   - Clean up old/unused databases
   - Monitor disk space usage

4. **Access Control**
   - Add user authentication (future)
   - Implement database-level permissions
   - Log all upload/delete operations

---

## 📈 Performance Optimization

1. **Large File Handling**
   - Use chunked reading for large CSVs
   - Implement progress tracking
   - Create indexes automatically
   - Use ANALYZE after data load

2. **Query Optimization**
   - Provide query hints to AI
   - Create appropriate indexes
   - Use EXPLAIN QUERY PLAN for analysis
   - Cache frequently accessed metadata

3. **Memory Management**
   - Stream large files instead of loading entirely
   - Use SQLite's memory-mapped I/O
   - Implement connection pooling

---

## 🐛 Troubleshooting Guide

### **Common Issues**

**Issue:** Upload fails with "Invalid file format"
- **Solution:** Ensure file has correct extension (.csv, .xlsx, .xls)

**Issue:** Database query returns no results
- **Solution:** Check table names with list_tables() tool

**Issue:** Column names look wrong
- **Solution:** Check sanitization - special characters are converted to underscores

**Issue:** Excel sheet not found
- **Solution:** Sheet names are sanitized - check describe_table() for actual name

---

## 🔄 Future Enhancements

1. **Advanced Features**
   - Support for compressed files (.zip, .gz)
   - JSON and Parquet file support
   - Automatic data profiling and quality checks
   - Data preview before conversion

2. **UI Improvements**
   - Drag-and-drop file organization
   - Database comparison tool
   - Visual schema designer
   - Query history and favorites

3. **Analytics**
   - Built-in data visualization
   - Automated insights generation
   - Export query results to CSV/Excel
   - Scheduled data refresh

---

## 📚 References

- [pandas Documentation](https://pandas.pydata.org/docs/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [FastAPI File Uploads](https://fastapi.tiangolo.com/tutorial/request-files/)
- [OpenRouter API](https://openrouter.ai/docs)

---

## ✅ Implementation Checklist

- [ ] Create `data_pipeline.py` module
- [ ] Add file upload endpoint to FastAPI
- [ ] Update SQLite MCP server for dynamic databases
- [ ] Enhance UI with upload components
- [ ] Add database selector dropdown
- [ ] Implement metadata management
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Update requirements.txt
- [ ] Create example datasets
- [ ] Write user documentation
- [ ] Test with real-world data

---

**Status:** Ready for implementation 🚀
**Priority:** High
**Estimated Time:** 6-8 hours for full implementation
