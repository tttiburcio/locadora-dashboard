import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

print("Fixing invalid qtd_itens formats...")
cur.execute("UPDATE os_itens SET qtd_itens = 2 WHERE id = 318") # specifically ID of the new item
print(f"Targeted fix complete. Affected: {cur.rowcount}")

# Auditing others
cur.execute("SELECT id, qtd_itens FROM os_itens")
bad = []
for rid, raw in cur.fetchall():
    if raw is None: continue
    try:
        int(raw)
    except:
        bad.append((rid, raw))

print(f"Found {len(bad)} extra bad rows in database.")
for rid, val in bad:
    # Quick extract digits
    import re
    num = re.findall(r'\d+', str(val))
    final = int(num[0]) if num else 1
    cur.execute("UPDATE os_itens SET qtd_itens = ? WHERE id = ?", (final, rid))
    print(f"  Fixed ID {rid}: '{val}' -> {final}")

conn.commit()
print("ALL DATA TYPE CORRECTED!")
conn.close()
