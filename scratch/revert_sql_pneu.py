import sqlite3

conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("UPDATE os_itens SET posicao_pneu = 'DIANTEIRO' WHERE id = 147")
conn.commit()
print(f"SQLite revert SUCCESS. Modified rows: {cur.rowcount}")
cur.execute("SELECT id, posicao_pneu, modelo_pneu FROM os_itens WHERE id = 147")
print("SQL Verification:", cur.fetchone())
conn.close()
