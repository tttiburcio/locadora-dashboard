import sqlite3

conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT id, numero_os, total_os FROM ordens_servico ORDER BY id DESC LIMIT 3")
print("Recent OS rows:")
for row in cur.fetchall():
    print(row)

cur.execute("SELECT id, numero_os, total_os FROM ordens_servico WHERE numero_os = 'OS-2026-0202'")
print("\nOS-2026-0202 matches:")
print(cur.fetchall())
conn.close()
