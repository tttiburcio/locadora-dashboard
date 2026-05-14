import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

for table in ['ordens_servico', 'os_itens', 'notas_fiscais', 'manutencao_parcelas']:
    cur.execute(f"PRAGMA table_info({table})")
    cols = [c[1] for c in cur.fetchall()]
    print(f"{table}: {cols}\n")

conn.close()
