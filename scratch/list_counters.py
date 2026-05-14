import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT * FROM os_counters")
for r in cur.fetchall():
    print(r)
conn.close()
