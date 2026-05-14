import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables in locadora.db:")
for r in cur.fetchall():
    print(r[0])
conn.close()
