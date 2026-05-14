import sqlite3
import requests

conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

# Counter exists, next count is ultimo + 1
cur.execute("SELECT ultimo FROM os_counters WHERE ano = 2026")
nxt = cur.fetchone()[0] + 1
os_num = f"OS-2026-{str(nxt).zfill(4)}"
print(f"Calculated Next OS Num: {os_num}")

cur.execute("SELECT id, modelo, implemento FROM frota WHERE placa = 'CSU3F94'")
veh = cur.fetchone()
print(f"Vehicle Metadata: {veh}")

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

print("\nQuerying KM from MAPWS...")
try:
    url = "http://localhost:8001/api/details/CSU3F94"
    params = {"start_date": "2026-01-16", "end_date": "2026-01-16"}
    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code == 200:
        recs = resp.json()
        if isinstance(recs, list) and recs:
             r = recs[-1]
             val = r.get("km_fim") or r.get("km_acumulado") or r.get("odometro")
             print("KM FOUND:", val)
        else:
             print("No recs returned.")
    else:
        print("MAPWS failed status:", resp.status_code)
except Exception as e:
    print("MAPWS Error:", e)
