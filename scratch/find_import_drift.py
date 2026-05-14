import pandas as pd
import sqlite3

path = r'c:\Users\ADM\Documents\locadora-dashboard\Locadora.xlsx'
xl = pd.ExcelFile(path)
sheet = next(s for s in xl.sheet_names if 'MANUTENCOES' in s)
df = xl.parse(sheet)
excel_ids = set(df['IDOrdServ'].dropna().unique())

conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT numero_os FROM ordens_servico WHERE numero_os IS NOT NULL")
db_ids = set(r[0] for r in cur.fetchall())
conn.close()

missing_in_db = excel_ids - db_ids
print(f"Found {len(missing_in_db)} OS IDs present in Excel but missing from DB.")
if missing_in_db:
    print("\nSample missing IDs:")
    print(sorted(list(missing_in_db))[:10])
    
    # Check if any of these missing IDs contain 2026 crossover data
    print("\nLooking for rows corresponding to missing IDs in Excel:")
    miss_rows = df[df['IDOrdServ'].isin(missing_in_db)]
    print(miss_rows[['Placa', 'IDOrdServ', 'DataExecução', 'Data Venc.', 'TotalOS']].tail(5))
