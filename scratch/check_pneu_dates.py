import sys, io, sqlite3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

conn = sqlite3.connect("locadora.db")
cur = conn.cursor()

# Check specific pneu OS from screenshot
target_os = ['OS-2026-0176', 'OS-2026-0188', 'OS-2025-0096']

print("=== ordens_servico ===")
for nos in target_os:
    cur.execute("""
        SELECT numero_os, placa, modelo, status_os,
               data_execucao, data_entrada, km
        FROM ordens_servico WHERE numero_os = ?
    """, (nos,))
    r = cur.fetchone()
    print(f"  {r}")

print("\n=== os_itens (pneu) ===")
for nos in target_os:
    cur.execute("""
        SELECT oi.id, os.numero_os, oi.sistema, oi.categoria,
               oi.posicao_pneu, oi.espec_pneu, oi.marca_pneu, oi.modelo_pneu, oi.qtd_pneu
        FROM os_itens oi JOIN ordens_servico os ON os.id = oi.os_id
        WHERE os.numero_os = ? AND LOWER(oi.sistema) = 'pneu'
    """, (nos,))
    rows = cur.fetchall()
    print(f"\n  {nos} - {len(rows)} items:")
    for r in rows:
        print(f"    {r}")

# Check ALL pneu OS without posicao_pneu in os_itens
print("\n=== Pneu OS finalizadas SEM posicao_pneu em os_itens ===")
cur.execute("""
    SELECT os.numero_os, os.placa, os.modelo, os.data_execucao,
           COUNT(oi.id) as total_items,
           SUM(CASE WHEN oi.posicao_pneu IS NOT NULL AND oi.posicao_pneu != '' THEN 1 ELSE 0 END) as items_com_pos
    FROM ordens_servico os
    JOIN os_itens oi ON oi.os_id = os.id
    WHERE os.deletado_em IS NULL
      AND os.status_os = 'finalizada'
      AND LOWER(oi.sistema) = 'pneu'
    GROUP BY os.id
    HAVING items_com_pos = 0
""")
rows = cur.fetchall()
print(f"Total: {len(rows)}")
for r in rows:
    print(f"  {r}")

# Check ALL pneu OS finalizadas - full picture
print("\n=== Todos pneu OS finalizadas: posicao e data_execucao ===")
cur.execute("""
    SELECT os.numero_os, os.placa, os.data_execucao,
           GROUP_CONCAT(DISTINCT oi.posicao_pneu) as posicoes,
           COUNT(oi.id) as items
    FROM ordens_servico os
    JOIN os_itens oi ON oi.os_id = os.id
    WHERE os.deletado_em IS NULL
      AND os.status_os = 'finalizada'
      AND LOWER(oi.sistema) = 'pneu'
    GROUP BY os.id
    ORDER BY os.data_execucao
""")
rows = cur.fetchall()
for r in rows:
    print(f"  {r}")

conn.close()
