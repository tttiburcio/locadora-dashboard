import sqlite3
import requests

conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

# 1. Get next OS count for 2026 from counter
cur.execute("SELECT proximo_id FROM os_counters WHERE ano = 2026")
res = cur.fetchone()
cnt = res[0] if res else 1
os_num = f"OS-2026-{str(cnt).zfill(4)}"
print(f"Next OS Num: {os_num}")

# 2. Get Vehicle Info
cur.execute("SELECT id, modelo, implemento FROM frota WHERE placa = 'CSU3F94'")
veh = cur.fetchone()
print(f"Vehicle Metadata: {veh}")

# 3. Get Contract on 16/01/2026
cur.execute("""
    SELECT c.id, c.empresa_id
    FROM contrato_veiculo cv
    JOIN contratos c ON c.id = cv.contrato_id
    WHERE cv.id_veiculo = ?
      AND (c.data_inicio IS NULL OR c.data_inicio <= '2026-01-16')
      AND (c.data_encerramento IS NULL OR c.data_encerramento >= '2026-01-16')
    ORDER BY c.data_inicio DESC LIMIT 1
""", (veh[0],))
con = cur.fetchone()
print(f"Active Contract: {con}")

conn.close()

# 4. Query KM from MAPWS
print("\nQuerying KM from MAPWS for 2026-01-16...")
try:
    url = "http://localhost:8001/api/details/CSU3F94"
    params = {"start_date": "2026-01-16", "end_date": "2026-01-16"}
    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        recs = data if isinstance(data, list) else (data.get("data") or [])
        if recs:
             r = recs[-1] if isinstance(recs, list) else recs
             val = r.get("km_fim") or r.get("km_acumulado") or r.get("odometro")
             print("KM FOUND:", val)
        else:
             print("No record for that day.")
    else:
        print("MAPWS connection failed.")
except Exception as e:
    print("MAPWS exception:", e)
