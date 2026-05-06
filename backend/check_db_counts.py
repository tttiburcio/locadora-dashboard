import sqlite3
import os

db_path = 'backend/manutencao.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    tables = ['ordens_servico', 'manutencoes', 'manutencao_parcelas', 'notas_fiscais']
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{table}: {count}")
        except Exception as e:
            print(f"Error checking {table}: {e}")
    conn.close()
