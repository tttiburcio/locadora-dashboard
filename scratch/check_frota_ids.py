import pandas as pd
import sqlite3

# 1. Check DB frota ID for EVF8I83
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT id, placa FROM frota WHERE placa = 'EVF8I83'")
db_frota = cur.fetchone()
print(f"DB Frota Record: {db_frota}")

# 2. Check Excel frota ID for EVF8I83
path = r'c:\Users\ADM\Documents\locadora-dashboard\Locadora.xlsx'
xl = pd.ExcelFile(path)
sheet = next(s for s in xl.sheet_names if 'FROTA' in s)
df = xl.parse(sheet)
ex_frota = df[df['Placa'] == 'EVF8I83'][['IDVeiculo', 'Placa']]
print("\nExcel Frota Record:")
print(ex_frota)

conn.close()
