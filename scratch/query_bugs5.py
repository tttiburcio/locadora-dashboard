import sqlite3

DB_PATH = r"c:\Users\vinic\Documents\clone\locadora.db"
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("=" * 70)
print("QUERY: data_execucao for the 16 OS involved in the false sinteticas")
print("=" * 70)
rows = conn.execute("""
    SELECT os.id, os.numero_os, os.data_execucao, os.data_entrada,
           nf.id as nf_id, nf.data_emissao
    FROM notas_fiscais nf
    JOIN ordens_servico os ON os.id = nf.os_id
    WHERE nf.id IN (172, 179, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 202)
    ORDER BY nf.id
""").fetchall()
for r in rows:
    print(dict(r))

print()
print("=" * 70)
print("QUERY: Check what dbListOs() returns for data_execucao on those OS")
print("       (simulating the frontend call)")
print("=" * 70)
rows2 = conn.execute("""
    SELECT id, numero_os, data_execucao, data_entrada, status_os
    FROM ordens_servico
    WHERE numero_os IN ('OS-2025-0133', 'OS-2025-0140', 'OS-2026-0145', 'OS-2026-0146',
                        'OS-2026-0147', 'OS-2026-0148', 'OS-2026-0149', 'OS-2026-0150',
                        'OS-2026-0151', 'OS-2026-0152', 'OS-2026-0153', 'OS-2026-0154',
                        'OS-2026-0155', 'OS-2026-0156', 'OS-2026-0158')
    ORDER BY numero_os
""").fetchall()
for r in rows2:
    print(dict(r))

print()
print("=" * 70)
print("QUERY: Final verification - sum of the 16 NF values")
print("=" * 70)
rows3 = conn.execute("""
    SELECT SUM(nf.valor_total_nf) as total
    FROM notas_fiscais nf
    WHERE nf.id IN (172, 179, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 202)
""").fetchall()
for r in rows3:
    print(dict(r))

conn.close()
print("Done.")
