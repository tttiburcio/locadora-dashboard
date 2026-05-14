import sys
sys.path.append(r'c:\Users\ADM\Documents\locadora-dashboard\backend')
import main
from fastapi.testclient import TestClient

client = TestClient(main.app)
resp = client.get("/api/maintenance_analysis/intervalos?sistema=Pneu")
data = resp.json()

# data is a dict { "data": [ ...list of vehicles... ] }
veiculos = data.get("data") if isinstance(data, dict) else data

csu = next((v for v in veiculos if v.get("placa") == 'CSU3F94'), None)
if csu:
    print("AUDITING SPLIT SETS FOR CSU3F94:")
    for med in csu.get("por_medida", []):
         print(f"\nMEDIDA: {med['espec']}")
         for c in med.get("conjuntos", []):
              s = "DISCARDED" if c.get("descartado") else "EM_USO"
              print(f"  -> {c.get('marca')} | Qty={c.get('qtd')} | OS={c.get('os_ref')} -> {s}")
else:
    print("CSU3F94 not found in vehicle lists:", [v.get("placa") for v in veiculos])
