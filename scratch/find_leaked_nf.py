import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

cur.execute("""
    SELECT DISTINCT os.numero_os, os.placa, nf.numero_nf, nf.valor_total_nf, nf.data_emissao
    FROM ordens_servico os
    JOIN notas_fiscais nf ON nf.os_id = os.id
    WHERE os.deletado_em IS NULL AND nf.deletado_em IS NULL
      AND strftime('%Y', COALESCE(os.data_execucao, os.data_entrada)) < '2026'
      AND strftime('%Y', nf.data_emissao) = '2026'
      AND NOT EXISTS (
          SELECT 1 FROM manutencao_parcelas p
          WHERE p.nf_id = nf.id AND p.deletado_em IS NULL
      )
""")
print("Leaked 2026 Notaries (OS < 2026, NF == 2026, No installments):")
for r in cur.fetchall():
    print(r)
conn.close()
