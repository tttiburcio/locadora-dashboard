import requests
import json

base_url = "http://localhost:8000/api/db/parcelas" # Assumindo porta 8000

try:
    # Vou tentar pegar as parcelas de 2026
    r = requests.get(base_url, params={"year": 2026})
    if r.status_code == 200:
        data = r.json()
        if data:
            print(f"Total parcelas: {len(data)}")
            # Procura a NF 916739 do print do usuário
            nf_target = "916739"
            p_target = [p for p in data if p.get('nota') == nf_target]
            if p_target:
                print(f"Dados da primeira parcela encontrada para NF {nf_target}:")
                print(json.dumps(p_target[0], indent=2))
            else:
                print(f"NF {nf_target} não encontrada nas primeiras parcelas.")
                print("Primeira parcela do dump:")
                print(json.dumps(data[0], indent=2))
    else:
        print(f"Erro na API: {r.status_code}")
except Exception as e:
    print(f"Erro ao conectar na API: {e}")
