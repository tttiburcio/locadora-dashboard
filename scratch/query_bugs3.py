import sqlite3

DB_PATH = r"c:\Users\vinic\Documents\clone\locadora.db"
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("=" * 70)
print("QUERY: Check the nfIdsComParcelas filter — the CORE of Bug #1")
print("=" * 70)
print()
print("The frontend calls dbListParcelas(year=2025) which returns parcelas")
print("filtered by: strftime('%Y', COALESCE(data_prevista_pagamento, data_vencimento)) = '2025'")
print()
print("Then it builds nfIdsComParcelas = set of nf_ids from these 2025 parcelas")
print()
print("Then for each OS's NF, if nf.id NOT in nfIdsComParcelas, it creates a 'sintetica'")
print("This means NFs that have parcelas BUT with data_vencimento in 2026 (not 2025)")
print("will have their nf_id excluded from nfIdsComParcelas for year=2025.")
print()

# Find NFs with parcelas in 2026 but data_emissao or os.data_execucao in 2025
rows = conn.execute("""
    SELECT nf.id as nf_id, nf.numero_nf, nf.data_emissao, nf.valor_total_nf,
           os.numero_os, os.data_execucao,
           (SELECT COUNT(*) FROM manutencao_parcelas mp
            WHERE mp.nf_id = nf.id AND mp.deletado_em IS NULL) as total_parcelas,
           (SELECT COUNT(*) FROM manutencao_parcelas mp
            WHERE mp.nf_id = nf.id AND mp.deletado_em IS NULL
            AND strftime('%Y', COALESCE(mp.data_prevista_pagamento, mp.data_vencimento)) = '2025') as parcelas_2025,
           (SELECT COUNT(*) FROM manutencao_parcelas mp
            WHERE mp.nf_id = nf.id AND mp.deletado_em IS NULL
            AND strftime('%Y', COALESCE(mp.data_prevista_pagamento, mp.data_vencimento)) = '2026') as parcelas_2026
    FROM notas_fiscais nf
    JOIN ordens_servico os ON os.id = nf.os_id
    WHERE nf.deletado_em IS NULL
      AND os.deletado_em IS NULL
      AND (
          strftime('%Y', nf.data_emissao) = '2025'
          OR strftime('%Y', os.data_execucao) = '2025'
      )
      -- NF has NO parcelas in 2025 (so it won't be in nfIdsComParcelas for year 2025)
      AND NOT EXISTS (
          SELECT 1 FROM manutencao_parcelas mp
          WHERE mp.nf_id = nf.id AND mp.deletado_em IS NULL
            AND strftime('%Y', COALESCE(mp.data_prevista_pagamento, mp.data_vencimento)) = '2025'
      )
      -- But DOES have parcelas in 2026
      AND EXISTS (
          SELECT 1 FROM manutencao_parcelas mp
          WHERE mp.nf_id = nf.id AND mp.deletado_em IS NULL
            AND strftime('%Y', COALESCE(mp.data_prevista_pagamento, mp.data_vencimento)) = '2026'
      )
    ORDER BY nf.id
""").fetchall()

total = 0.0
print(f"NFs with 2025 date but parcelas ONLY in 2026 (these become false 'sinteticas' in 2025 financeiro):")
for r in rows:
    d = dict(r)
    total += float(d['valor_total_nf'] or 0)
    print(f"  nf_id={d['nf_id']}, nr={d['numero_nf']}, emissao={d['data_emissao']}, "
          f"valor={d['valor_total_nf']}, os={d['numero_os']}, exec={d['data_execucao']}, "
          f"parcelas_2025={d['parcelas_2025']}, parcelas_2026={d['parcelas_2026']}, total_parcelas={d['total_parcelas']}")
print(f"Total: {len(rows)} NFs, total valor = R${total:.2f}")

print()
print("=" * 70)
print("QUERY: Also check NFs that have NO parcelas at all but are in 2025")
print("=" * 70)
rows2 = conn.execute("""
    SELECT nf.id as nf_id, nf.numero_nf, nf.data_emissao, nf.valor_total_nf,
           os.numero_os, os.data_execucao
    FROM notas_fiscais nf
    JOIN ordens_servico os ON os.id = nf.os_id
    WHERE nf.deletado_em IS NULL
      AND os.deletado_em IS NULL
      AND (
          strftime('%Y', nf.data_emissao) = '2025'
          OR strftime('%Y', os.data_execucao) = '2025'
      )
      AND NOT EXISTS (
          SELECT 1 FROM manutencao_parcelas mp
          WHERE mp.nf_id = nf.id AND mp.deletado_em IS NULL
      )
    ORDER BY nf.id
""").fetchall()
total2 = 0.0
print(f"NFs with 2025 date and NO parcelas at all:")
for r in rows2:
    d = dict(r)
    total2 += float(d['valor_total_nf'] or 0)
    print(f"  {d}")
print(f"Total: {len(rows2)} NFs, total valor = R${total2:.2f}")

conn.close()
print("Done.")
