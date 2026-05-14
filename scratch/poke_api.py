import requests

url = "http://localhost:8000/api/db/os"
try:
    resp = requests.get(url, timeout=5)
    print(f"STATUS: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"SUCCESS! Returned {len(data)} OS records.")
        if data:
             print("First item snapshot:", {k: data[0][k] for k in ['id', 'numero_os', 'empresa', 'id_contrato']})
    else:
        print("ERROR BODY:", resp.text)
except Exception as e:
    print("API UNREACHABLE:", e)
