import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("PRAGMA table_info(os_itens)")
print("Schema of os_itens:")
for r in cur.fetchall():
    print(r)
conn.close()
