import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT id, numero_os, placa, total_os, data_execucao, criado_em FROM ordens_servico WHERE deletado_em IS NULL ORDER BY criado_em DESC LIMIT 10")
print("Absolute Newest OS Entries:")
for r in cur.fetchall():
    print(r)
conn.close()
