import sqlite3

DB_PATH = r"c:\Users\vinic\Documents\clone\locadora.db"
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("=" * 70)
print("QUERY: Check if manutencoes table has data_execucao (legacy model)")
print("=" * 70)
rows = conn.execute("""
    SELECT COUNT(*) as total,
           COUNT(data_execucao) as with_data_execucao,
           COUNT(CASE WHEN data_execucao IS NULL THEN 1 END) as without_data_execucao
    FROM manutencoes
""").fetchall()
for r in rows:
    print(dict(r))

print()
print("=" * 70)
print("QUERY: Sample manutencoes with their data_execucao")
print("=" * 70)
rows = conn.execute("""
    SELECT id, status_manutencao, id_ord_serv, data_execucao, placa
    FROM manutencoes
    LIMIT 10
""").fetchall()
for r in rows:
    print(dict(r))

print()
print("=" * 70)
print("QUERY: manutencao_parcelas that link to legacy manutencoes (not nf_id)")
print("=" * 70)
rows = conn.execute("""
    SELECT COUNT(*) as total_legacy,
           SUM(mp.valor_parcela) as valor_total
    FROM manutencao_parcelas mp
    WHERE mp.manutencao_id IS NOT NULL
      AND mp.nf_id IS NULL
      AND mp.deletado_em IS NULL
""").fetchall()
for r in rows:
    print(dict(r))

print()
print("=" * 70)
print("QUERY: Check table schema for manutencao_parcelas")
print("=" * 70)
rows = conn.execute("PRAGMA table_info(manutencao_parcelas)").fetchall()
for r in rows:
    print(dict(r))

print()
print("=" * 70)
print("QUERY: 2025 parcelas nf_id IS NULL (legacy)")
print("=" * 70)
rows = conn.execute("""
    SELECT mp.id, mp.data_vencimento, mp.valor_parcela, mp.status_pagamento,
           mp.nf_id, mp.manutencao_id,
           m.data_execucao as manut_data_execucao
    FROM manutencao_parcelas mp
    LEFT JOIN manutencoes m ON m.id = mp.manutencao_id
    WHERE mp.deletado_em IS NULL
      AND mp.nf_id IS NULL
      AND strftime('%Y', COALESCE(mp.data_prevista_pagamento, mp.data_vencimento)) = '2025'
    LIMIT 10
""").fetchall()
print(f"Count: {len(rows)}")
for r in rows:
    print(dict(r))

print()
print("=" * 70)
print("QUERY: Parcelas in 2025 via nf_id path — check data_execucao availability")
print("=" * 70)
rows = conn.execute("""
    SELECT mp.id, mp.status_pagamento,
           mp.nf_id, nf.data_emissao,
           os.data_execucao as os_data_execucao, os.numero_os,
           mp.data_vencimento
    FROM manutencao_parcelas mp
    JOIN notas_fiscais nf ON nf.id = mp.nf_id
    JOIN ordens_servico os ON os.id = nf.os_id
    WHERE mp.deletado_em IS NULL
      AND nf.deletado_em IS NULL
      AND strftime('%Y', COALESCE(mp.data_prevista_pagamento, mp.data_vencimento)) = '2025'
      AND os.data_execucao IS NULL
    LIMIT 10
""").fetchall()
print(f"Parcelas in 2025 where OS has no data_execucao: {len(rows)}")
for r in rows:
    print(dict(r))

conn.close()
print("Done.")
