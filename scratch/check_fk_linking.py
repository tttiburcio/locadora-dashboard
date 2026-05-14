import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT id, numero_os, placa, id_veiculo, total_os FROM ordens_servico WHERE numero_os IN ('OS-2026-0215', 'OS-2026-0213')")
print("IDVeiculo linking state:")
for r in cur.fetchall():
    print(r)
conn.close()
