import sqlite3
import pandas as pd
import sys

# Set stdout to utf-8 just in case
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def check_db():
    conn = sqlite3.connect('locadora.db')
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()
    print("Tables:", tables)
    
    # Check faturamento table schema
    cur.execute("PRAGMA table_info(faturamento);")
    columns = cur.fetchall()
    print("\n'faturamento' Table Columns:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    conn.close()

def check_xlsx():
    try:
        xl = pd.ExcelFile('Locadora.xlsx')
        print("\nSheets:", [s.encode('ascii', 'replace').decode('ascii') for s in xl.sheet_names])
        
        # Read faturamento if exists
        sheet = next((s for s in xl.sheet_names if 'faturamento' in s.lower()), None)
        if sheet:
            df = pd.read_excel('Locadora.xlsx', sheet_name=sheet)
            print(f"\nSheet '{sheet}' summary:")
            print(f"  Rows: {len(df)}")
            print(f"  Columns: {df.columns.tolist()}")
            print("\nFirst 3 rows:\n", df.head(3).to_string())
        else:
            print("\nFaturamento sheet not found.")
    except Exception as e:
        print(f"Error reading XLSX: {e}")

if __name__ == "__main__":
    check_db()
    check_xlsx()
