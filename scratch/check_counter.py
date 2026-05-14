import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT * FROM os_counters WHERE ano = 2025")
print("OS Counter for 2025:", cur.fetchone())
conn.close()
