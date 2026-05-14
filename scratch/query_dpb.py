import urllib.request
import json

try:
    with urllib.request.urlopen("http://localhost:8000/api/vehicles?year=2026") as response:
        data = json.loads(response.read().decode())
    
    vehicles = data.get("vehicles", [])
    target = next((v for v in vehicles if v.get("placa") == "DPB8E26"), None)
    
    if target:
        print("LIVE API VEHICLE DATA FOR DPB8E26:")
        print(f"Custo Manutenção: {target.get('custo_manutencao')}")
    else:
        print("Vehicle DPB8E26 not found in live API response.")
        
except Exception as e:
    print("Error querying live API:", e)
