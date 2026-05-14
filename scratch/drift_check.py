import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

print("Checking 'ordens_servico':")
cur.execute("SELECT numero_os FROM ordens_servico WHERE numero_os LIKE '%021%'")
for r in cur.fetchall():
    print(r)

print("\nChecking 'manutencoes':")
cur.execute("SELECT id_ord_serv FROM manutencoes WHERE id_ord_serv LIKE '%021%'")
for r in cur.fetchall():
    print(r)

conn.close()
