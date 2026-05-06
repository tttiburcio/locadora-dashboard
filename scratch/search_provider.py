import sqlite3
from pathlib import Path

db_path = Path('locadora.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Buscando parcelas da DIBRACAM...")
cursor.execute("SELECT id, nota, parcela_atual, parcela_total, data_vencimento FROM manutencao_parcelas WHERE fornecedor LIKE '%DIBRACAM%' ORDER BY id DESC LIMIT 10")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
