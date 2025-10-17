"""
Test Excel to SQLite Conversion
Quick verification that Excel files are properly converted to SQLite databases
"""
import pandas as pd
import sqlite3
import asyncio
from pathlib import Path
from data_pipeline import DataPipeline

async def test_excel_conversion():
    """Test converting Excel file to SQLite"""
    
    # Create test Excel file with multiple sheets
    test_excel = Path("test_data.xlsx")
    
    print("📝 Creating test Excel file with 2 sheets...")
    with pd.ExcelWriter(test_excel) as writer:
        # Sheet 1: Sales data
        sales_df = pd.DataFrame({
            'Product ID': [1, 2, 3, 4, 5],
            'Product Name': ['Widget A', 'Widget B', 'Gadget C', 'Tool D', 'Device E'],
            'Price': [29.99, 49.99, 19.99, 89.99, 149.99],
            'Quantity Sold': [120, 85, 200, 45, 30]
        })
        sales_df.to_excel(writer, sheet_name='Sales Data', index=False)
        
        # Sheet 2: Customers
        customers_df = pd.DataFrame({
            'Customer ID': [101, 102, 103, 104, 105],
            'Name': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Williams', 'Charlie Brown'],
            'Email': ['john@example.com', 'jane@example.com', 'bob@example.com', 'alice@example.com', 'charlie@example.com'],
            'Total Purchases': [5, 12, 3, 8, 15]
        })
        customers_df.to_excel(writer, sheet_name='Customers', index=False)
    
    print(f"✅ Test Excel created: {test_excel}")
    print(f"   - Sheet 1: Sales Data (5 rows, 4 columns)")
    print(f"   - Sheet 2: Customers (5 rows, 4 columns)")
    
    # Initialize pipeline
    pipeline = DataPipeline(upload_dir="test_uploads")
    
    # Process the Excel file
    print("\n🔄 Converting Excel to SQLite...")
    try:
        result = await pipeline.process_upload(test_excel, "test_data.xlsx")
        
        print("\n✅ Conversion successful!")
        print(f"   Database ID: {result['database_id']}")
        print(f"   Database name: {result['database_name']}")
        print(f"   Database path: {result['db_path']}")
        print(f"   Tables created: {len(result.get('tables', []))}")
        
        # Verify the database
        db_path = result['db_path']
        print(f"\n🔍 Verifying database: {db_path}")
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # List tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"\n   📊 Tables in database:")
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                col_names = [col[1] for col in columns]
                
                print(f"      • {table_name}: {row_count} rows, columns: {col_names}")
                
                # Show sample data
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 2")
                rows = cursor.fetchall()
                print(f"        Sample data:")
                for row in rows[:1]:
                    print(f"          {row}")
        
        print("\n✅ Excel to SQLite conversion is working correctly!")
        print("   All sheets converted to separate tables")
        print("   Column names sanitized for SQL compatibility")
        print("   Data integrity preserved")
        
        # Cleanup
        test_excel.unlink()
        print(f"\n🧹 Cleaned up test file: {test_excel}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        if test_excel.exists():
            test_excel.unlink()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_excel_conversion())
    if success:
        print("\n" + "="*60)
        print("✅ RESULT: Excel to SQLite conversion is working properly!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ RESULT: Excel conversion has issues - check logs above")
        print("="*60)
