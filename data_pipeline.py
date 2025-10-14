"""
Data Pipeline Module
Handles CSV/Excel file uploads and conversion to SQLite databases
"""
import pandas as pd
import sqlite3
import json
import uuid
import re
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

SQL_RESERVED_WORDS = {
    'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'TABLE', 'INDEX',
    'CREATE', 'DROP', 'ALTER', 'ORDER', 'BY', 'GROUP', 'HAVING', 'JOIN',
    'INNER', 'OUTER', 'LEFT', 'RIGHT', 'ON', 'AS', 'UNION', 'DISTINCT'
}


class DataPipeline:
    """Handle CSV/Excel to SQLite conversion with metadata management"""
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.db_dir = self.upload_dir / "databases"
        self.original_dir = self.upload_dir / "original_files"
        self.metadata_file = self.upload_dir / "metadata.json"
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Create required directories if they don't exist"""
        self.upload_dir.mkdir(exist_ok=True)
        self.db_dir.mkdir(exist_ok=True)
        self.original_dir.mkdir(exist_ok=True)
        logger.info(f"Upload directories initialized at {self.upload_dir}")
        
    def sanitize_column_name(self, name: str) -> str:
        """
        Clean column names for SQL compatibility
        
        Args:
            name: Original column name
            
        Returns:
            Sanitized column name safe for SQL
        """
        # Remove leading/trailing whitespace
        name = str(name).strip()
        
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
        
    async def process_upload(self, file_path: Path, original_filename: str) -> Dict[str, Any]:
        """
        Main entry point for file processing
        
        Args:
            file_path: Path to uploaded file
            original_filename: Original filename from upload
            
        Returns:
            Dictionary with processing results and metadata
        """
        file_ext = file_path.suffix.lower()
        db_id = str(uuid.uuid4())
        db_name = f"{db_id}"
        
        logger.info(f"Processing upload: {original_filename} (type: {file_ext})")
        
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
            
            logger.info(f"Upload processed successfully: {db_id}")
            
            return {
                "database_id": db_id,
                "database_name": metadata["name"],
                **result
            }
            
        except Exception as e:
            logger.error(f"Upload processing failed: {e}")
            raise
            
    async def convert_csv_to_sqlite(self, csv_path: Path, db_name: str) -> Dict:
        """
        Convert CSV file to SQLite database
        
        Args:
            csv_path: Path to CSV file
            db_name: Name for the database file (without extension)
            
        Returns:
            Dictionary with conversion results
        """
        logger.info(f"Reading CSV file: {csv_path}")
        
        try:
            # Read CSV with various encoding attempts
            try:
                df = pd.read_csv(csv_path, encoding='utf-8-sig')
            except UnicodeDecodeError:
                df = pd.read_csv(csv_path, encoding='latin-1')
            
            if df.empty:
                raise ValueError("CSV file is empty")
            
            if len(df.columns) == 0:
                raise ValueError("CSV has no columns")
            
            # Sanitize column names
            original_columns = df.columns.tolist()
            df.columns = [self.sanitize_column_name(col) for col in df.columns]
            
            logger.info(f"CSV loaded: {len(df)} rows, {len(df.columns)} columns")
            
            # Create database
            db_path = self.db_dir / f"{db_name}.db"
            
            with sqlite3.connect(db_path) as conn:
                # Write data to SQLite
                df.to_sql('data', conn, if_exists='replace', index=False)
                
                # Create index on first column if it looks like an ID
                first_col = df.columns[0]
                if 'id' in first_col.lower() or first_col.lower() in ['index', 'key']:
                    try:
                        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{first_col} ON data({first_col})")
                    except Exception as e:
                        logger.warning(f"Could not create index: {e}")
                
                conn.commit()
            
            logger.info(f"SQLite database created: {db_path}")
            
            return {
                "success": True,
                "db_path": str(db_path),
                "table_name": "data",
                "row_count": len(df),
                "column_count": len(df.columns)
            }
            
        except pd.errors.EmptyDataError:
            logger.error("CSV file is empty or has no data")
            raise ValueError("CSV file contains no data")
        except pd.errors.ParserError as e:
            logger.error(f"CSV parsing error: {e}")
            raise ValueError(f"Invalid CSV format: {str(e)}")
        except Exception as e:
            logger.error(f"CSV conversion failed: {e}")
            raise
        
    async def convert_excel_to_sqlite(self, excel_path: Path, db_name: str) -> Dict:
        """
        Convert Excel file (all sheets) to SQLite database
        
        Args:
            excel_path: Path to Excel file
            db_name: Name for the database file (without extension)
            
        Returns:
            Dictionary with conversion results
        """
        logger.info(f"Reading Excel file: {excel_path}")
        
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(excel_path)
            sheet_names = excel_file.sheet_names
            
            if not sheet_names:
                raise ValueError("Excel file has no sheets")
            
            logger.info(f"Excel file has {len(sheet_names)} sheets: {sheet_names}")
            
            db_path = self.db_dir / f"{db_name}.db"
            tables_info = []
            
            with sqlite3.connect(db_path) as conn:
                for sheet_name in sheet_names:
                    # Read sheet
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    
                    if df.empty:
                        logger.warning(f"Sheet '{sheet_name}' is empty, skipping")
                        continue
                    
                    # Sanitize table name
                    table_name = self.sanitize_column_name(sheet_name)
                    
                    # Sanitize column names
                    df.columns = [self.sanitize_column_name(col) for col in df.columns]
                    
                    # Write to database
                    df.to_sql(table_name, conn, if_exists='replace', index=False)
                    
                    # Create index on first column if appropriate
                    first_col = df.columns[0]
                    if 'id' in first_col.lower():
                        try:
                            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{first_col} ON {table_name}({first_col})")
                        except Exception as e:
                            logger.warning(f"Could not create index on {table_name}: {e}")
                    
                    tables_info.append({
                        "name": table_name,
                        "row_count": len(df),
                        "column_count": len(df.columns)
                    })
                    
                    logger.info(f"Sheet '{sheet_name}' -> table '{table_name}': {len(df)} rows")
                
                conn.commit()
            
            logger.info(f"SQLite database created with {len(tables_info)} tables: {db_path}")
            
            return {
                "success": True,
                "db_path": str(db_path),
                "tables": tables_info,
                "total_rows": sum(t["row_count"] for t in tables_info)
            }
            
        except Exception as e:
            logger.error(f"Excel conversion failed: {e}")
            raise
        
    def _save_metadata(self, new_metadata: Dict):
        """
        Save database metadata to JSON file
        
        Args:
            new_metadata: Metadata dictionary for new database
        """
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"databases": [], "active_database_id": None}
        
        data["databases"].append(new_metadata)
        
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Metadata saved for database: {new_metadata['id']}")
            
    def list_databases(self) -> Dict:
        """
        List all uploaded databases
        
        Returns:
            Dictionary with list of databases
        """
        if not self.metadata_file.exists():
            return {"databases": [], "active_database_id": None}
        
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read metadata: {e}")
            return {"databases": [], "active_database_id": None}
            
    def get_database_by_id(self, db_id: str) -> Dict:
        """
        Get database metadata by ID
        
        Args:
            db_id: Database ID
            
        Returns:
            Database metadata dictionary
            
        Raises:
            ValueError: If database not found
        """
        data = self.list_databases()
        for db in data.get("databases", []):
            if db["id"] == db_id:
                return db
        raise ValueError(f"Database not found: {db_id}")
    
    def update_active_database(self, db_id: str):
        """
        Mark a database as active and others as inactive
        
        Args:
            db_id: Database ID to mark as active
        """
        data = self.list_databases()
        
        for db in data["databases"]:
            db["is_active"] = (db["id"] == db_id)
        
        data["active_database_id"] = db_id
        
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Active database updated to: {db_id}")
    
    def delete_database(self, db_id: str):
        """
        Delete a database and its associated files
        
        Args:
            db_id: Database ID to delete
        """
        db_metadata = self.get_database_by_id(db_id)
        
        # Delete database file
        db_path = Path(db_metadata["db_path"])
        if db_path.exists():
            db_path.unlink()
            logger.info(f"Deleted database file: {db_path}")
        
        # Delete original file
        for ext in ['.csv', '.xlsx', '.xls']:
            original_path = self.original_dir / f"{db_id}{ext}"
            if original_path.exists():
                original_path.unlink()
                logger.info(f"Deleted original file: {original_path}")
        
        # Remove from metadata
        data = self.list_databases()
        data["databases"] = [db for db in data["databases"] if db["id"] != db_id]
        
        if data["active_database_id"] == db_id:
            data["active_database_id"] = None
        
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Database deleted: {db_id}")
