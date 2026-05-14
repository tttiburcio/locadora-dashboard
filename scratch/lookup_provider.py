import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT id, nome FROM fornecedores WHERE UPPER(nome) LIKE '%GP PNEUS%'")
print("Fornecedor Lookup:", cur.fetchone())
conn.close()
