import sqlite3

DB = r'C:\Users\vinic\Documents\clone\locadora.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Find OS-2026-0203
row = conn.execute("SELECT id, numero_os, status_os, indisponivel, fornecedor, empresa FROM ordens_servico WHERE numero_os = 'OS-2026-0203'").fetchone()
print('OS:', dict(row) if row else None)

if row:
    os_id = row['id']
    nfs = conn.execute("SELECT id, numero_nf, fornecedor, empresa_faturada, valor_total_nf, data_emissao FROM notas_fiscais WHERE os_id = ?", (os_id,)).fetchall()
    print(f'\nNFs ({len(nfs)} total):')
    for nf in nfs:
        d = dict(nf)
        print(f"  id={d['id']} numero_nf={d['numero_nf']!r} fornecedor={d['fornecedor']!r} empresa={d['empresa_faturada']!r} valor={d['valor_total_nf']} emissao={d['data_emissao']}")

conn.close()
