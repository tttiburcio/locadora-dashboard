import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

cur.execute("PRAGMA table_info(contratos)")
print("Contratos schema:", [c[1] for c in cur.fetchall()])

print("\nListing some contracts with their linked company info:")
cur.execute("SELECT id, nome_cliente, empresa_id, empresa_locadora FROM contratos LIMIT 5")
for r in cur.fetchall():
    print(r)

conn.close()
