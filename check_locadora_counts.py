import sqlite3
import os

db_path = 'locadora.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
tables = ['ordens_servico', 'manutencoes', 'manutencao_parcelas', 'notas_fiscais']
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"{table}: {count}")
conn.close()
