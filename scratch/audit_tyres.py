import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

queries = [
    "SELECT id, marca_pneu, modelo_pneu FROM os_itens WHERE LOWER(marca_pneu) LIKE '%apollo%' OR LOWER(modelo_pneu) LIKE '%apollo%'",
    "SELECT id, marca_pneu, modelo_pneu FROM os_itens WHERE LOWER(marca_pneu) LIKE '%eurovan%' OR LOWER(modelo_pneu) LIKE '%eurovan%'",
    "SELECT id, marca_pneu, modelo_pneu FROM os_itens WHERE LOWER(marca_pneu) LIKE '%vancontact%' OR LOWER(modelo_pneu) LIKE '%vancontact%'",
    "SELECT id, marca_pneu, modelo_pneu FROM os_itens WHERE LOWER(marca_pneu) LIKE '%cargoplus%' OR LOWER(modelo_pneu) LIKE '%cargoplus%'",
    "SELECT id, marca_pneu, modelo_pneu FROM os_itens WHERE id IN (20, 229)"
]

for q in queries:
    print(f"Running: {q}")
    cur.execute(q)
    for r in cur.fetchall():
        print("  Result:", r)

conn.close()
