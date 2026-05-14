import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

# Update the position in SQLite as well
cur.execute("UPDATE os_itens SET posicao_pneu = 'TRASEIRO' WHERE id = 147")
conn.commit()
print(f"SQLite update success. Rows modified: {cur.rowcount}")

cur.execute("SELECT id, posicao_pneu, marca_pneu, modelo_pneu FROM os_itens WHERE id = 147")
print("Verification:", cur.fetchone())

conn.close()
