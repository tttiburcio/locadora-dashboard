import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("""
    SELECT os.numero_os, p.data_vencimento, p.valor_parcela, p.valor_atualizado
    FROM ordens_servico os
    JOIN notas_fiscais nf ON nf.os_id = os.id
    JOIN manutencao_parcelas p ON p.nf_id = nf.id
    WHERE os.numero_os = 'OS-2026-0193'
""")
print("Details for OS-2026-0193:")
for r in cur.fetchall():
    print(r)
conn.close()
