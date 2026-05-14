import sys
import os
sys.path.append(r'c:\Users\ADM\Documents\locadora-dashboard\backend')

import main
from fastapi.testclient import TestClient

client = TestClient(main.app)
print("Starting system integration test with new quantity-aware logic...")

try:
    # Target the intervals endpoint for tires specifically to trigger the logic!
    resp = client.get("/api/maintenance_analysis/intervalos?sistema=Pneu")
    print(f"API HTTP STATUS: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"SUCCESS! Retrieved data for {len(data)} vehicles.")
        
        # Find the target vehicle in output
        csu = next((v for v in data if v.get("placa") == 'CSU3F94'), None)
        if csu:
            print("Found CSU3F94 in output, checking sets...")
            # Count datasets under the especificacao group
            for group in csu.get("por_medida", []):
                 print(f"Group {group['espec']} sets:")
                 for c in group["conjuntos"]:
                      status = "DESCARTE" if c.get("descartado") else "EM_USO"
                      print(f"  -> OS {c.get('os_ref')} | Qtd {c.get('qtd')} | {c['marca']} -> {status}")
        else:
             print("Target vehicle not found in results.")
    else:
        print("API Failed logic execution:", resp.text)
        
except Exception as e:
    print("CRITICAL SYSTEM CRASH AFTER PATCH:", e)
