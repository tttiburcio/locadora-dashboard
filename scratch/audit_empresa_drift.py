import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

print("Auditing 'empresa' values in ordens_servico:")
cur.execute("SELECT empresa, COUNT(*) FROM ordens_servico GROUP BY 1")
for r in cur.fetchall():
    print("  ", r)

print("\nAuditing 'empresa_faturada' in linked notas_fiscais:")
cur.execute("SELECT empresa_faturada, COUNT(*) FROM notas_fiscais GROUP BY 1")
for r in cur.fetchall():
    print("  ", r)

conn.close()
