import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("PRAGMA table_info(notas_fiscais)")
print("Schema of notas_fiscais:")
for r in cur.fetchall():
    print(r)
conn.close()
