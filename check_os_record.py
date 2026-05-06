import sqlite3
conn = sqlite3.connect('locadora.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT * FROM ordens_servico LIMIT 1")
row = cursor.fetchone()
if row:
    print(dict(row))
else:
    print("No records found in ordens_servico")
conn.close()
