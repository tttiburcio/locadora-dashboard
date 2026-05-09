import sys, io, sqlite3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

conn = sqlite3.connect("locadora.db")
cur = conn.cursor()

# 1. Check pending parcelas for 2025 (should be 0)
print("=== Parcelas Pendente com vencimento em 2025 ===")
cur.execute("""
    SELECT mp.id, mp.data_vencimento, mp.valor_parcela, mp.status_pagamento,
           mp.nf_id, mp.manutencao_id, mp.deletado_em
    FROM manutencao_parcelas mp
    WHERE mp.status_pagamento = 'Pendente'
      AND mp.deletado_em IS NULL
      AND strftime('%Y', mp.data_vencimento) = '2025'
""")
rows = cur.fetchall()
print(f"Total: {len(rows)}")
for r in rows:
    print(f"  {r}")

# 2. Check NFs without parcelas that have data_emissao or OS data_execucao in 2025
print("\n=== NFs sem parcelas com data em 2025 (causam sintéticas falsas) ===")
cur.execute("""
    SELECT nf.id, nf.os_id, nf.valor_total_nf, nf.data_emissao,
           os.numero_os, os.data_execucao, os.data_entrada,
           COUNT(mp.id) as n_parcelas_total,
           COUNT(CASE WHEN mp.deletado_em IS NULL THEN 1 END) as n_parcelas_ativas
    FROM notas_fiscais nf
    JOIN ordens_servico os ON os.id = nf.os_id
    LEFT JOIN manutencao_parcelas mp ON mp.nf_id = nf.id
    WHERE nf.deletado_em IS NULL
      AND os.deletado_em IS NULL
      AND (
        strftime('%Y', nf.data_emissao) = '2025'
        OR strftime('%Y', COALESCE(os.data_execucao, os.data_entrada)) = '2025'
      )
    GROUP BY nf.id
    HAVING n_parcelas_ativas = 0 AND nf.valor_total_nf > 0
    ORDER BY os.data_execucao
""")
rows = cur.fetchall()
print(f"Total NFs sem parcelas: {len(rows)}")
for r in rows:
    print(f"  nf_id={r[0]} os_id={r[1]} valor={r[2]} data_emissao={r[3]} OS={r[4]} exec={r[5]} entrada={r[6]} parc_total={r[7]} parc_ativas={r[8]}")

# 3. Check pneu OS with data_execucao issues
print("\n=== OS de Pneu: data_execucao NULL vs preenchido ===")
cur.execute("""
    SELECT
        COUNT(*) as total,
        COUNT(CASE WHEN os.data_execucao IS NOT NULL THEN 1 END) as com_exec,
        COUNT(CASE WHEN os.data_execucao IS NULL AND os.data_entrada IS NOT NULL THEN 1 END) as so_entrada,
        COUNT(CASE WHEN os.data_execucao IS NULL AND os.data_entrada IS NULL THEN 1 END) as sem_data
    FROM ordens_servico os
    JOIN os_itens oi ON oi.os_id = os.id
    WHERE os.deletado_em IS NULL
      AND os.status_os = 'finalizada'
      AND LOWER(oi.sistema) = 'pneu'
""")
r = cur.fetchone()
print(f"  Total OS pneu: {r[0]}, com data_exec: {r[1]}, só entrada: {r[2]}, sem data: {r[3]}")

# 4. Check OS executed in 2025 with parcelas only in 2026 (bug 2)
print("\n=== OS exec 2025 com parcelas só em 2026 (bug análise) ===")
cur.execute("""
    SELECT os.id, os.numero_os, os.data_execucao, os.data_entrada,
           SUM(mp.valor_parcela) as total_parc,
           MIN(strftime('%Y', mp.data_vencimento)) as ano_min_parc,
           MAX(strftime('%Y', mp.data_vencimento)) as ano_max_parc
    FROM ordens_servico os
    JOIN notas_fiscais nf ON nf.os_id = os.id AND nf.deletado_em IS NULL
    JOIN manutencao_parcelas mp ON mp.nf_id = nf.id AND mp.deletado_em IS NULL
    WHERE os.deletado_em IS NULL
      AND strftime('%Y', COALESCE(os.data_execucao, os.data_entrada)) = '2025'
    GROUP BY os.id
    HAVING MIN(strftime('%Y', mp.data_vencimento)) > '2025'
    ORDER BY os.data_execucao
""")
rows = cur.fetchall()
print(f"Total OS afetadas: {len(rows)}")
for r in rows:
    print(f"  OS={r[1]} exec={r[2]} entrada={r[3]} total={r[4]} parc_anos={r[5]}~{r[6]}")

conn.close()
