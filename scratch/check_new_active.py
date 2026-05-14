import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT numero_os, placa, total_os, data_execucao, criado_em FROM ordens_servico WHERE deletado_em IS NULL ORDER BY id DESC LIMIT 5")
print("Last 5 NOT deleted OS:")
for r in cur.fetchall():
    print(r)
conn.close()
