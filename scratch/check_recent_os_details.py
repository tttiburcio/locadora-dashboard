import sqlite3

conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

cur.execute("""
    SELECT os.numero_os, os.placa, os.total_os, COALESCE(os.data_execucao, os.data_entrada) as data_os
    FROM ordens_servico os
    WHERE os.numero_os IN ('OS-2026-0213', 'OS-2026-0214', 'OS-2026-0215')
""")
print("Recent OS Details:")
for row in cur.fetchall():
    print(row)

conn.close()
