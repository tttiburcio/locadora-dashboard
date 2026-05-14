import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("""
    SELECT p.id, p.data_vencimento, p.valor_parcela
    FROM ordens_servico os
    JOIN notas_fiscais nf ON nf.os_id = os.id
    JOIN manutencao_parcelas p ON p.nf_id = nf.id
    WHERE os.numero_os = 'OS-2026-0208'
""")
print("ALL Installments for OS-2026-0208:")
for r in cur.fetchall():
    print(r)
conn.close()
