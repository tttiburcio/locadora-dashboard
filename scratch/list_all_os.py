import sqlite3

conn = sqlite3.connect(r'c:\Users\ADM\Documents\locadora-dashboard\locadora.db')
cur = conn.cursor()
cur.execute("SELECT numero_os FROM ordens_servico WHERE deletado_em IS NULL ORDER BY numero_os")
res = [r[0] for r in cur.fetchall() if r[0]]
conn.close()

print(" | ".join(res))
print(f"\nTotal active OS in SQL: {len(res)}")
