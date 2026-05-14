import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

print("Detecting casing issues in espec_pneu:")
cur.execute("SELECT espec_pneu, COUNT(*) FROM os_itens GROUP BY 1")
for r in cur.fetchall():
    print(" ", r)

conn.close()
