import os
from pathlib import Path

root = Path(r"c:\Users\ADM\Documents\locadora-dashboard")
db = root / "locadora.db"
excel = root / "Locadora.xlsx"

print(f"DB Path exists: {db.exists()} - {db}")
print(f"Excel Path exists: {excel.exists()} - {excel}")
