import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

# Find OS where at least one NF has installments, but another NF does NOT.
cur.execute("""
    SELECT DISTINCT os.numero_os, os.placa, nf.numero_nf, nf.valor_total_nf
    FROM ordens_servico os
    JOIN notas_fiscais nf ON nf.os_id = os.id
    WHERE os.deletado_em IS NULL AND nf.deletado_em IS NULL
      AND EXISTS (
          SELECT 1 FROM notas_fiscais nf2
          JOIN manutencao_parcelas p ON p.nf_id = nf2.id
          WHERE nf2.os_id = os.id AND p.deletado_em IS NULL
      )
      AND NOT EXISTS (
          SELECT 1 FROM manutencao_parcelas p
          WHERE p.nf_id = nf.id AND p.deletado_em IS NULL
      )
""")
print("List of partially parcelled OS (NF has no installments while other NF in same OS does):")
for r in cur.fetchall():
    print(r)
conn.close()
