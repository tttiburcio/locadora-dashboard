import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

# Sum all TotalOS directly without case splitting for year 2026
cur.execute("""
    SELECT SUM(COALESCE(os.total_os, (SELECT SUM(valor_total_nf) FROM notas_fiscais WHERE os_id = os.id AND deletado_em IS NULL), 0))
    FROM ordens_servico os
    WHERE os.placa = 'DPB8E26' AND os.deletado_em IS NULL
      AND strftime('%Y', COALESCE(os.data_execucao, os.data_entrada)) = '2026'
""")
print("Total full cost of 2026 executed OS for DPB8E26:", cur.fetchone()[0])

# Now count the CURRENT split value 
# (just replicating the logic from backend/main.py for this single plate)
query = """
    SELECT SUM(
       CASE
         WHEN EXISTS (
           SELECT 1 FROM notas_fiscais nf
           JOIN manutencao_parcelas p ON p.nf_id = nf.id
           WHERE nf.os_id = os.id AND nf.deletado_em IS NULL AND p.deletado_em IS NULL
         )
         THEN COALESCE(
           (SELECT SUM(p.valor_parcela)
            FROM manutencao_parcelas p
            JOIN notas_fiscais nf ON nf.id = p.nf_id
            WHERE nf.os_id = os.id
              AND p.deletado_em IS NULL
              AND nf.deletado_em IS NULL
              AND strftime('%Y', p.data_vencimento) = '2026'),
           0
         )
         ELSE COALESCE(os.total_os, (SELECT SUM(valor_total_nf) FROM notas_fiscais WHERE os_id = os.id AND deletado_em IS NULL), 0)
       END
    )
    FROM ordens_servico os
    WHERE os.placa = 'DPB8E26' AND os.deletado_em IS NULL
      AND (
        EXISTS (
          SELECT 1 FROM notas_fiscais nf
          JOIN manutencao_parcelas p ON p.nf_id = nf.id
          WHERE nf.os_id = os.id AND nf.deletado_em IS NULL AND p.deletado_em IS NULL
            AND strftime('%Y', p.data_vencimento) = '2026'
        )
        OR strftime('%Y', COALESCE(os.data_execucao, os.data_entrada)) = '2026'
      )
"""
cur.execute(query)
print("Split value currently calculated by backend query:", cur.fetchone()[0])

conn.close()
