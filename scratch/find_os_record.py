import sqlite3

conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

print("Locating OS-2025-0112 in database:")
cur.execute("""
    SELECT oi.id, os.numero_os, oi.posicao_pneu, oi.marca_pneu, oi.modelo_pneu
    FROM os_itens oi
    JOIN ordens_servico os ON os.id = oi.os_id
    WHERE os.numero_os = 'OS-2025-0112'
""")
results = cur.fetchall()
for r in results:
    print("  SQL Entry:", r)

conn.close()
