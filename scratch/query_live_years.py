import urllib.request
import json

try:
    with urllib.request.urlopen("http://localhost:8000/api/years") as response:
        data = json.loads(response.read().decode())
    print("API Available Years:", data.get("years"))
except Exception as e:
    print("Error querying api/years:", e)
