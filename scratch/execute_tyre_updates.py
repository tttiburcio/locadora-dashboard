import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

updates = [
    ("UPDATE os_itens SET marca_pneu = 'APOLLO' WHERE UPPER(marca_pneu) = 'APOLLO ALTRUST'", "Apollo Altrust -> APOLLO"),
    ("UPDATE os_itens SET marca_pneu = 'CONTINENTAL' WHERE UPPER(marca_pneu) = 'GENERAL EUROVAN'", "General Eurovan -> CONTINENTAL"),
    ("UPDATE os_itens SET marca_pneu = 'CONTINENTAL' WHERE UPPER(marca_pneu) = 'CONTINENTAL VANCONTACT'", "CONTINENTAL VANCONTACT -> CONTINENTAL"),
    ("UPDATE os_itens SET marca_pneu = 'XBRI' WHERE UPPER(marca_pneu) = 'CARGOPLUS'", "CARGOPLUS -> XBRI"),
    ("UPDATE os_itens SET marca_pneu = 'GOODYEAR' WHERE id = 229", "ID 229 -> GOODYEAR"),
    ("UPDATE os_itens SET marca_pneu = 'XBRI' WHERE id = 20", "ID 20 -> XBRI"),
]

print("Executing SQL updates:")
for sql, desc in updates:
    cur.execute(sql)
    print(f"  [OK] {desc} - {cur.rowcount} rows affected.")

conn.commit()
conn.close()
print("Database committed successfully.")
