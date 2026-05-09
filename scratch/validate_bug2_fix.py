import sys, io, sqlite3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

conn = sqlite3.connect("locadora.db")

# Simula a nova WHERE clause do backend para year=2025
import sqlite3
cur = conn.cursor()
cur.execute("""
    SELECT os.numero_os, os.data_execucao, os.data_entrada,
           COALESCE(os.total_os,
               (SELECT SUM(nf2.valor_total_nf) FROM notas_fiscais nf2
                WHERE nf2.os_id = os.id AND nf2.deletado_em IS NULL), 0
           ) as total_os_fallback,
           CASE
             WHEN EXISTS (
               SELECT 1 FROM notas_fiscais nf JOIN manutencao_parcelas p ON p.nf_id = nf.id
               WHERE nf.os_id = os.id AND nf.deletado_em IS NULL AND p.deletado_em IS NULL
                 AND strftime('%Y', p.data_vencimento) = '2025'
             )
             THEN COALESCE(
               (SELECT SUM(p.valor_parcela) FROM manutencao_parcelas p
                JOIN notas_fiscais nf ON nf.id = p.nf_id
                WHERE nf.os_id = os.id AND p.deletado_em IS NULL AND nf.deletado_em IS NULL
                  AND strftime('%Y', p.data_vencimento) = '2025'), 0)
             ELSE COALESCE(os.total_os,
               (SELECT SUM(valor_total_nf) FROM notas_fiscais WHERE os_id = os.id AND deletado_em IS NULL), 0)
           END as TotalOS_calculado
    FROM ordens_servico os
    WHERE os.deletado_em IS NULL
      AND (
        EXISTS (
          SELECT 1 FROM notas_fiscais nf JOIN manutencao_parcelas p ON p.nf_id = nf.id
          WHERE nf.os_id = os.id AND nf.deletado_em IS NULL AND p.deletado_em IS NULL
            AND strftime('%Y', p.data_vencimento) = '2025'
        )
        OR strftime('%Y', COALESCE(os.data_execucao, os.data_entrada)) = '2025'
      )
    ORDER BY COALESCE(os.data_execucao, os.data_entrada)
""")
rows = cur.fetchall()

total_2025 = sum(r[4] for r in rows if r[4])
print(f"Total OS incluídas em 2025 (nova query): {len(rows)}")
print(f"Total custo manutenção 2025: R$ {total_2025:,.2f}")

# Quais OS foram adicionadas pelo novo critério (exec_date = 2025, sem parcelas 2025)
cur.execute("""
    SELECT os.numero_os, os.data_execucao,
           COALESCE(os.total_os,
               (SELECT SUM(nf2.valor_total_nf) FROM notas_fiscais nf2
                WHERE nf2.os_id = os.id AND nf2.deletado_em IS NULL), 0
           ) as total
    FROM ordens_servico os
    WHERE os.deletado_em IS NULL
      AND strftime('%Y', COALESCE(os.data_execucao, os.data_entrada)) = '2025'
      AND NOT EXISTS (
        SELECT 1 FROM notas_fiscais nf JOIN manutencao_parcelas p ON p.nf_id = nf.id
        WHERE nf.os_id = os.id AND nf.deletado_em IS NULL AND p.deletado_em IS NULL
          AND strftime('%Y', p.data_vencimento) = '2025'
      )
    ORDER BY os.data_execucao
""")
new_rows = cur.fetchall()
print(f"\nOS recuperadas pelo novo critério (exec 2025, parcelas em outro ano): {len(new_rows)}")
for r in new_rows:
    print(f"  {r[0]} | exec={r[1]} | custo=R${r[2]:,.2f}")
print(f"  Subtotal recuperado: R${sum(r[2] for r in new_rows if r[2]):,.2f}")

conn.close()
