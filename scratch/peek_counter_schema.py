import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("PRAGMA table_info(os_counters)")
print([c[1] for c in cur.fetchall()])
cur.execute("SELECT * FROM os_counters")
print(cur.fetchall())
conn.close()
