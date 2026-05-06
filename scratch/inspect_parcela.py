import sqlite3
from pathlib import Path

db_path = Path('locadora.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Buscando TODAS as parcelas que contenham '923535' no campo nota...")
cursor.execute("SELECT id, nota, parcela_atual, parcela_total, data_vencimento, deletado_em, fornecedor FROM manutencao_parcelas WHERE nota LIKE '%923535%'")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
