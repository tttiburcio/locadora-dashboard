import sqlite3
from pathlib import Path

db_path = Path('locadora.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

os_num = 'OS-2026-0177'
print(f"Buscando itens da {os_num}...")
cursor.execute("SELECT id, sistema, servico, descricao FROM os_itens WHERE os_id = (SELECT id FROM ordens_servico WHERE numero_os = ?)", (os_num,))
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
