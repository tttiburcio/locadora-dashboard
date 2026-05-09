import sqlite3

DB_PATH = r"c:\Users\vinic\Documents\clone\locadora.db"
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("=" * 70)
print("QUERY A: nf_ids that have parcelas with data_vencimento in 2025")
print("(this is what nfIdsComParcelas would contain for year=2025)")
print("=" * 70)
rows = conn.execute("""
    SELECT DISTINCT mp.nf_id
    FROM manutencao_parcelas mp
    WHERE mp.deletado_em IS NULL
      AND mp.nf_id IS NOT NULL
      AND (
          strftime('%Y', COALESCE(mp.data_prevista_pagamento, mp.data_vencimento)) = '2025'
      )
""").fetchall()
nf_ids_com_parcelas_2025 = set(r['nf_id'] for r in rows)
print(f"NF IDs with parcelas in year 2025: {nf_ids_com_parcelas_2025}")

print()
print("=" * 70)
print("QUERY B: ALL NFs with their os data_execucao year")
print("(looking for NFs NOT in the 2025 parcelas set but with 2025 data)")
print("=" * 70)
rows = conn.execute("""
    SELECT nf.id as nf_id, nf.numero_nf, nf.data_emissao, nf.valor_total_nf,
           nf.deletado_em as nf_deletado,
           os.id as os_id, os.numero_os, os.data_execucao, os.status_os,
           os.deletado_em as os_deletado,
           (SELECT COUNT(*) FROM manutencao_parcelas WHERE nf_id = nf.id AND deletado_em IS NULL) as parcelas_count
    FROM notas_fiscais nf
    JOIN ordens_servico os ON os.id = nf.os_id
    WHERE nf.deletado_em IS NULL
      AND os.deletado_em IS NULL
      AND (
          strftime('%Y', nf.data_emissao) = '2025'
          OR strftime('%Y', os.data_execucao) = '2025'
      )
    ORDER BY nf.id
""").fetchall()

print(f"Total NFs matching 2025 by data_emissao or data_execucao: {len(rows)}")
for r in rows:
    d = dict(r)
    in_set = d['nf_id'] in nf_ids_com_parcelas_2025
    print(f"  nf_id={d['nf_id']}, nr={d['numero_nf']}, emissao={d['data_emissao']}, "
          f"valor={d['valor_total_nf']}, os={d['numero_os']}, exec={d['data_execucao']}, "
          f"parcelas_count={d['parcelas_count']}, in_2025_nfIds={in_set}")

print()
print("=" * 70)
print("QUERY C: NFs with 2025 data_emissao OR data_execucao that have NO parcelas")
print("(these become 'sinteticas' and appear as Pendente in the frontend)")
print("=" * 70)
rows = conn.execute("""
    SELECT nf.id as nf_id, nf.numero_nf, nf.data_emissao, nf.valor_total_nf,
           os.numero_os, os.data_execucao, os.status_os,
           (SELECT COUNT(*) FROM manutencao_parcelas WHERE nf_id = nf.id AND deletado_em IS NULL) as parcelas_count
    FROM notas_fiscais nf
    JOIN ordens_servico os ON os.id = nf.os_id
    WHERE nf.deletado_em IS NULL
      AND os.deletado_em IS NULL
      AND NOT EXISTS (
          SELECT 1 FROM manutencao_parcelas mp2
          WHERE mp2.nf_id = nf.id AND mp2.deletado_em IS NULL
      )
      AND (
          strftime('%Y', nf.data_emissao) = '2025'
          OR strftime('%Y', os.data_execucao) = '2025'
      )
    ORDER BY nf.id
""").fetchall()

print(f"NFs with 2025 date and NO parcelas: {len(rows)}")
total = 0.0
for r in rows:
    d = dict(r)
    total += float(d['valor_total_nf'] or 0)
    print(f"  nf_id={d['nf_id']}, nr={d['numero_nf']}, emissao={d['data_emissao']}, "
          f"valor={d['valor_total_nf']}, os={d['numero_os']}, exec={d['data_execucao']}, status={d['status_os']}")
print(f"Total value of these NFs: R${total:.2f}")

print()
print("=" * 70)
print("QUERY D: All parcelas for year 2025 (any data_vencimento or data_prevista_pagamento)")
print("=" * 70)
rows = conn.execute("""
    SELECT mp.id, mp.data_vencimento, mp.valor_parcela, mp.status_pagamento,
           mp.nf_id, mp.manutencao_id, mp.deletado_em
    FROM manutencao_parcelas mp
    WHERE mp.deletado_em IS NULL
      AND strftime('%Y', COALESCE(mp.data_prevista_pagamento, mp.data_vencimento)) = '2025'
""").fetchall()
print(f"Total parcelas in 2025 (by the backend filter): {len(rows)}")
for r in rows:
    print(f"  {dict(r)}")

print()
print("=" * 70)
print("QUERY E: Check all parcelas in DB by year")
print("=" * 70)
rows = conn.execute("""
    SELECT strftime('%Y', data_vencimento) as year, COUNT(*) as count, SUM(valor_parcela) as total
    FROM manutencao_parcelas
    WHERE deletado_em IS NULL
    GROUP BY 1
    ORDER BY 1
""").fetchall()
for r in rows:
    print(dict(r))

conn.close()
print("Done.")
