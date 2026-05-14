import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT id, marca_pneu, modelo_pneu FROM os_itens WHERE id IN (10, 20, 92, 93, 94, 147, 182, 185, 200, 201, 202, 229, 239, 241, 242, 251, 264) ORDER BY marca_pneu")
print("FINAL VERIFICATION STATE:")
for r in cur.fetchall():
    print(" ", r)
conn.close()
