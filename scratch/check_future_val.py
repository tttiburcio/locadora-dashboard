import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("""
    SELECT os.numero_os, os.placa, os.data_execucao, p.data_vencimento, p.valor_parcela
    FROM ordens_servico os
    JOIN notas_fiscais nf ON nf.os_id = os.id
    JOIN manutencao_parcelas p ON p.nf_id = nf.id
    WHERE strftime('%Y', COALESCE(os.data_execucao, os.data_entrada)) = '2026'
      AND strftime('%Y', p.data_vencimento) != '2026'
""")
print("2026 executions with non-2026 installments:")
for r in cur.fetchall():
    print(r)
conn.close()
