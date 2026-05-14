import urllib.request
import json

try:
    with urllib.request.urlopen("http://localhost:8000/api/vehicles?year=2026") as response:
        data = json.loads(response.read().decode())
    vehicles = data.get("vehicles", [])
    evf = next((v for v in vehicles if v.get("placa") == "EVF8I83"), None)
    
    if evf:
        print(json.dumps(evf, indent=2))
        
        # Check derived math manually
        c_manut = evf.get("custo_manutencao", 0)
        c_seg = evf.get("custo_seguro", 0)
        c_imp = evf.get("custo_impostos", 0)
        c_rast = evf.get("custo_rastreamento", 0)
        
        sum_costs = c_manut + c_seg + c_imp + c_rast
        stored_total = evf.get("custo_total", 0)
        
        print(f"\nSUM of individual costs: {sum_costs}")
        print(f"STORED custo_total: {stored_total}")
        print(f"Delta: {stored_total - sum_costs}")
except Exception as e:
    print(e)
