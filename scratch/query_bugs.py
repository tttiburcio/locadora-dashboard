import sqlite3

DB_PATH = r"c:\Users\vinic\Documents\clone\locadora.db"
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("=" * 70)
print("QUERY 1: Pending parcelas in 2025")
print("=" * 70)
rows = conn.execute("""
    SELECT mp.id, mp.data_vencimento, mp.valor_parcela, mp.status_pagamento,
           mp.manutencao_id, mp.nf_id, mp.deletado_em
    FROM manutencao_parcelas mp
    WHERE mp.status_pagamento = 'Pendente'
      AND strftime('%Y', mp.data_vencimento) = '2025'
    LIMIT 30
""").fetchall()
for r in rows:
    print(dict(r))

print()
print("=" * 70)
print("QUERY 2: Pending parcelas 2025 with nf_id vs manutencao_id")
print("=" * 70)
rows = conn.execute("""
    SELECT mp.id, mp.data_vencimento, mp.valor_parcela, mp.status_pagamento,
           mp.nf_id, mp.manutencao_id, mp.deletado_em,
           nf.deletado_em as nf_deletado_em,
           os.deletado_em as os_deletado_em,
           os.status_os
    FROM manutencao_parcelas mp
    LEFT JOIN notas_fiscais nf ON nf.id = mp.nf_id
    LEFT JOIN ordens_servico os ON os.id = nf.os_id
    WHERE mp.status_pagamento = 'Pendente'
      AND strftime('%Y', mp.data_vencimento) = '2025'
""").fetchall()
total_val = 0.0
for r in rows:
    d = dict(r)
    total_val += float(d['valor_parcela'] or 0)
    print(d)
print(f"Total value: R${total_val:.2f}")

print()
print("=" * 70)
print("QUERY 3: ordens_servico with NULL data_execucao")
print("=" * 70)
rows = conn.execute("""
    SELECT id, numero_os, data_execucao, data_entrada, status_os, deletado_em
    FROM ordens_servico
    WHERE data_execucao IS NULL
    ORDER BY id
    LIMIT 20
""").fetchall()
for r in rows:
    print(dict(r))

print()
print("=" * 70)
print("QUERY 4: notas_fiscais deletado_em stats")
print("=" * 70)
rows = conn.execute("""
    SELECT COUNT(*) as total,
           COUNT(CASE WHEN deletado_em IS NOT NULL THEN 1 END) as deleted
    FROM notas_fiscais
""").fetchall()
for r in rows:
    print(dict(r))

print()
print("=" * 70)
print("QUERY 5: manutencao_parcelas deletado_em stats")
print("=" * 70)
rows = conn.execute("""
    SELECT COUNT(*) as total,
           COUNT(CASE WHEN deletado_em IS NOT NULL THEN 1 END) as deleted
    FROM manutencao_parcelas
""").fetchall()
for r in rows:
    print(dict(r))

print()
print("=" * 70)
print("QUERY 6: Sample of ordens_servico - check data_execucao values")
print("=" * 70)
rows = conn.execute("""
    SELECT id, numero_os, data_execucao, data_entrada, status_os
    FROM ordens_servico
    WHERE deletado_em IS NULL
    ORDER BY id DESC
    LIMIT 20
""").fetchall()
for r in rows:
    print(dict(r))

print()
print("=" * 70)
print("QUERY 7: Count OS with/without data_execucao")
print("=" * 70)
rows = conn.execute("""
    SELECT
        COUNT(*) as total,
        COUNT(data_execucao) as with_data_execucao,
        COUNT(CASE WHEN data_execucao IS NULL THEN 1 END) as without_data_execucao,
        COUNT(data_entrada) as with_data_entrada
    FROM ordens_servico
    WHERE deletado_em IS NULL
""").fetchall()
for r in rows:
    print(dict(r))

print()
print("=" * 70)
print("QUERY 8: parcelas with nf_id where nf is deleted")
print("=" * 70)
rows = conn.execute("""
    SELECT COUNT(*) as parcelas_with_deleted_nf,
           SUM(mp.valor_parcela) as total_valor
    FROM manutencao_parcelas mp
    JOIN notas_fiscais nf ON nf.id = mp.nf_id
    WHERE mp.deletado_em IS NULL
      AND mp.status_pagamento = 'Pendente'
      AND nf.deletado_em IS NOT NULL
      AND strftime('%Y', mp.data_vencimento) = '2025'
""").fetchall()
for r in rows:
    print(dict(r))

print()
print("=" * 70)
print("QUERY 9: parcelas with manutencao_id (legacy) for 2025")
print("=" * 70)
rows = conn.execute("""
    SELECT COUNT(*) as count, SUM(valor_parcela) as total
    FROM manutencao_parcelas
    WHERE deletado_em IS NULL
      AND status_pagamento = 'Pendente'
      AND nf_id IS NULL
      AND manutencao_id IS NOT NULL
      AND strftime('%Y', data_vencimento) = '2025'
""").fetchall()
for r in rows:
    print(dict(r))

conn.close()
print("Done.")
