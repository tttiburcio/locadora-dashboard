import pandas as pd
import sqlite3

path = r'c:\Users\ADM\Documents\locadora-dashboard\Locadora.xlsx'
xl = pd.ExcelFile(path)
sheet = next(s for s in xl.sheet_names if 'MANUTENCOES' in s)
df = xl.parse(sheet)
df = df.dropna(subset=['Placa'])

df['DataExecução'] = pd.to_datetime(df['DataExecução'], errors='coerce')

# 1. Excel rows potentially lost by current compute() filter
excel_lost = df[df['DataExecução'].isna()].copy()

# 2. Load existing DB records
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT numero_os FROM ordens_servico")
db_ids = set(str(r[0]).strip().upper() for r in cur.fetchall() if r[0])
conn.close()

# 3. Intersect: Which ones aren't in DB and thus won't be rescued by SQL loading step?
excel_lost['IDOrdServ_norm'] = excel_lost['IDOrdServ'].astype(str).str.strip().str.upper()
ultimate_lost = excel_lost[~excel_lost['IDOrdServ_norm'].isin(db_ids)]

print(f"CRITICAL FINDINGS: Found {len(ultimate_lost)} EXCEL ROWS THAT ARE COMPLETELY INVISIBLE TO THE DASHBOARD.")
if not ultimate_lost.empty:
    print("\nDetails of invisible rows currently missing from vehicle summary:")
    print(ultimate_lost[['Placa', 'IDOrdServ', 'Data Venc.', 'TotalOS', 'Fornecedor']])
else:
    print("Wait... no ultimate lost rows found? Let me check again.")
