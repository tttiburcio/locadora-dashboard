import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM manutencoes")
print("Row count in manutencoes:", cur.fetchone()[0])
conn.close()
