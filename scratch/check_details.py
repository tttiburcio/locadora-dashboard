import sqlite3
from pathlib import Path

db_path = Path('locadora.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Detalhes da NF 923535...")
cursor.execute("SELECT id, nota, parcela_atual, parcela_total, valor_parcela, data_vencimento, fornecedor FROM manutencao_parcelas WHERE nota = '923535'")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
