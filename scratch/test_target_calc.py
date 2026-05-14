import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

cur.execute("""
    SELECT
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
       END as TotalOS
    FROM ordens_servico os
    WHERE os.numero_os = 'OS-2026-0189'
""")
print("Calculated current TotalOS for OS-2026-0189:", cur.fetchone()[0])

# Check installments in DB again
cur.execute("""
    SELECT p.data_vencimento, p.valor_parcela, p.deletado_em, nf.deletado_em
    FROM manutencao_parcelas p
    JOIN notas_fiscais nf ON nf.id = p.nf_id
    JOIN ordens_servico os ON os.id = nf.os_id
    WHERE os.numero_os = 'OS-2026-0189'
""")
print("Raw Installments for OS-2026-0189:")
for r in cur.fetchall():
    print(r)

conn.close()
