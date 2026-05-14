import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("PRAGMA table_info(manutencao_parcelas)")
print("Schema of manutencao_parcelas:")
for r in cur.fetchall():
    print(r)
conn.close()
