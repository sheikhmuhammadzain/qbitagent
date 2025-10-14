# 📊 Example Data Files

These sample files are provided to help you test the CSV/Excel to SQLite data pipeline.

## Available Files

### 1. `sales_data.csv`
Simple sales data with 10 rows demonstrating basic CSV upload functionality.

**Columns:**
- Date: Transaction date
- Product: Product name (Widget A, B, or C)
- Quantity: Number of items sold
- Price: Unit price
- Total: Total sale amount

## How to Use

1. **Start the server:**
   ```bash
   python run_fixed.py
   ```

2. **Open the web UI:**
   - Navigate to http://localhost:8000

3. **Upload a file:**
   - Drag and drop `sales_data.csv` onto the upload zone, OR
   - Click "Browse Files" and select the file

4. **Query your data:**
   - Once uploaded, the database will be automatically selected
   - Try these example queries:
     - "What's the total revenue?"
     - "Which product sold the most quantity?"
     - "Show me all sales from January 5th onwards"
     - "What's the average price per product?"
     - "List all transactions sorted by total amount"

## Expected Results

After uploading `sales_data.csv`:
- **Database created:** sales_data.db
- **Table name:** data
- **Rows:** 10
- **Columns:** 5 (date, product, quantity, price, total)

The AI will automatically use SQL queries via the MCP tools to answer your questions!

## Creating Your Own Test Files

### CSV Format
```csv
Column1,Column2,Column3
Value1,Value2,Value3
Value4,Value5,Value6
```

### Excel Format
- Create a `.xlsx` file with one or more sheets
- Each sheet will become a separate table in the database
- Column names will be sanitized (special characters → underscores)

## Tips

- **File Size:** Maximum 100MB per file
- **Supported Formats:** CSV (.csv), Excel (.xlsx, .xls)
- **Column Names:** Use letters, numbers, and underscores for best results
- **Data Types:** Pandas will automatically infer data types (integers, floats, text)
- **Multiple Databases:** You can upload multiple files and switch between them using the dropdown

## Troubleshooting

**Upload fails:**
- Check file format is CSV or Excel
- Ensure file size is under 100MB
- Verify the file is not corrupted

**Can't see data:**
- Use the database selector dropdown to switch databases
- Click the refresh button (🔄) to reload the database list
- Check that you've selected a database before querying

**Wrong results:**
- Use "list_tables" to see available tables
- Use "describe_table" to view column names and types
- Column names are automatically sanitized (e.g., "Product Name" becomes "product_name")

---

**Need more help?** Check `DATA_PIPELINE_PLAN.md` and `DATA_PIPELINE_QUICKSTART.md` for detailed documentation!
