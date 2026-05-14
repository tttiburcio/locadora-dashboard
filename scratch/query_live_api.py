import urllib.request
import json

try:
    with urllib.request.urlopen("http://localhost:8000/api/vehicles?year=2026") as response:
        data = json.loads(response.read().decode())
    
    vehicles = data.get("vehicles", [])
    evf = next((v for v in vehicles if v.get("placa") == "EVF8I83"), None)
    
    if evf:
        print("LIVE API VEHICLE DATA FOR EVF8I83:")
        print(f"Custo Manutenção: {evf.get('custo_manutencao')}")
        print(f"Custo Total: {evf.get('custo_total')}")
    else:
        print("Vehicle EVF8I83 not found in live API response.")
        
    # Also check EJX
    ejx = next((v for v in vehicles if v.get("placa") == "EJX0I24"), None)
    if ejx:
        print("\nLIVE API VEHICLE DATA FOR EJX0I24:")
        print(f"Custo Manutenção: {ejx.get('custo_manutencao')}")
except Exception as e:
    print("Error querying live API:", e)
