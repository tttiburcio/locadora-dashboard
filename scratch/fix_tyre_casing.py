import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

cur.execute("UPDATE os_itens SET espec_pneu = UPPER(espec_pneu) WHERE espec_pneu = '225/75r16c'")
conn.commit()
print(f"Sanitization complete. Rows updated: {cur.rowcount}")

conn.close()
