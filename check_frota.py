import sqlite3
conn = sqlite3.connect('locadora.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM frota")
print(f"frota: {cursor.fetchone()[0]}")
conn.close()
