import requests
import sqlite3
import pandas as pd

conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

# 1. Vehicle details
print("--- Step 1: Lookup Vehicle Metadata ---")
cur.execute("SELECT id, modelo, implemento FROM frota WHERE placa = 'CSU3F94'")
frota = cur.fetchone()
if not frota:
    # Fallback to excel
    print("Vehicle not found in SQL 'frota' table. Checking excel...")
    # Load from excel
    xl = pd.ExcelFile(r'c:\Users\ADM\Documents\locadora-dashboard\Locadora.xlsx')
    sheet = next(s for s in xl.sheet_names if 'FROTA' in s)
    df = xl.parse(sheet)
    match = df[df['Placa'] == 'CSU3F94']
    if not match.empty:
        frota = (match.iloc[0]['IDVeiculo'], match.iloc[0]['Modelo'], match.iloc[0]['Implemento'])
        print("Found in Excel:", frota)
else:
    print("Found in SQL:", frota)

# 2. Get next OS number for 2025
print("\n--- Step 2: Generating next OS number for 2025 ---")
cur.execute("SELECT MAX(SUBSTR(numero_os, 9)) FROM ordens_servico WHERE numero_os LIKE 'OS-2025-%'")
max_val = cur.fetchone()[0]
next_idx = int(max_val) + 1 if max_val else 1
next_os = f"OS-2025-{str(next_idx).zfill(4)}"
print("New OS Number:", next_os)

conn.close()

# 3. Query MAPWS
print("\n--- Step 3: Fetching KM from MAPWS ---")
try:
    url = "http://localhost:8001/api/details/CSU3F94"
    params = {"start_date": "2025-12-18", "end_date": "2025-12-18"}
    resp = requests.get(url, params=params, timeout=10)
    print("MAPWS Status:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        recs = data if isinstance(data, list) else (data.get("data") or [])
        if recs:
             r = recs[-1] if isinstance(recs, list) else recs
             val = r.get("km_fim") or r.get("km_acumulado") or r.get("odometro")
             print("KM FOUND:", val)
        else:
             print("No records returned for that day.")
    else:
        print("Failed to contact MAPWS.")
except Exception as e:
    print("Error connecting to MAPWS:", e)
