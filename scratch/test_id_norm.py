import pandas as pd
import sqlite3

path = r'c:\Users\ADM\Documents\locadora-dashboard\Locadora.xlsx'
xl = pd.ExcelFile(path)
sheet = next(s for s in xl.sheet_names if 'MANUTENCOES' in s)
df = xl.parse(sheet)
excel_ids = set(str(x).strip().upper() for x in df['IDOrdServ'].dropna().unique())

conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT numero_os FROM ordens_servico WHERE numero_os IS NOT NULL")
db_ids = set(str(r[0]).strip().upper() for r in cur.fetchall())
conn.close()

print(f"Total Excel IDs: {len(excel_ids)}")
print(f"Total DB IDs: {len(db_ids)}")
overlap = excel_ids.intersection(db_ids)
print(f"Intersection: {len(overlap)}")

if len(excel_ids) != len(overlap):
    print("DIFF: Items in Excel NOT in DB after normalization:")
    print(excel_ids - overlap)
