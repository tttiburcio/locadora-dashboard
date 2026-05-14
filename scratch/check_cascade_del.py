import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("""
    SELECT nf.id, nf.deletado_em as nf_del, p.id, p.deletado_em as p_del
    FROM ordens_servico os
    JOIN notas_fiscais nf ON nf.os_id = os.id
    JOIN manutencao_parcelas p ON p.nf_id = nf.id
    WHERE os.numero_os = 'OS-2026-0201'
""")
print("Soft deletion status for components of OS-2026-0201:")
for r in cur.fetchall():
    print(r)
conn.close()
