import sqlite3

conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

cur.execute("""
    SELECT os.numero_os, nf.numero_nf, p.data_vencimento, p.valor_parcela, p.valor_atualizado
    FROM ordens_servico os
    LEFT JOIN notas_fiscais nf ON nf.os_id = os.id
    LEFT JOIN manutencao_parcelas p ON p.nf_id = nf.id
    WHERE os.numero_os IN ('OS-2026-0213', 'OS-2026-0214', 'OS-2026-0215')
    ORDER BY os.numero_os DESC
""")
print("Installment details for recent OS:")
for row in cur.fetchall():
    print(row)

conn.close()
