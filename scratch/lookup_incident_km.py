import requests
try:
    url = "http://localhost:8001/api/details/CSU3F94"
    params = {"start_date": "2026-01-06", "end_date": "2026-01-06"}
    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code == 200:
        recs = resp.json()
        if recs:
             r = recs[-1] if isinstance(recs, list) else recs
             print("KM for Jan 6:", r.get("km_fim") or r.get("km_acumulado") or r.get("odometro"))
        else:
             print("No rec found.")
    else:
        print("Fail status", resp.status_code)
except Exception as e:
    print(e)
