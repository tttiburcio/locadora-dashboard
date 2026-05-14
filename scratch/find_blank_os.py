import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("""
    SELECT id, numero_os, placa, criado_em
    FROM ordens_servico os
    WHERE os.deletado_em IS NULL 
      AND (os.total_os IS NULL OR os.total_os = 0)
      AND NOT EXISTS (SELECT 1 FROM notas_fiscais nf WHERE nf.os_id = os.id AND nf.deletado_em IS NULL)
    ORDER BY criado_em DESC
""")
print("Active OS without TotalOS and without Notas Fiscais:")
for r in cur.fetchall():
    print(r)
conn.close()
