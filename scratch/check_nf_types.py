import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT tipo_nf, COUNT(*) FROM notas_fiscais GROUP BY 1")
for r in cur.fetchall():
    print(r)
conn.close()
