import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT id, nome_cliente, empresa_id FROM contratos LIMIT 5")
for r in cur.fetchall():
    print(r)
conn.close()
