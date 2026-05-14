import sqlite3
conn = sqlite3.connect('locadora.db')

# Get OS-2025-0026 and OS-2026-0217 items
os_rows = conn.execute("""
SELECT os.numero_os, os.placa, os.km, 
       COALESCE(os.data_execucao, os.data_entrada) as data_exec,
       oi.posicao_pneu, oi.qtd_pneu, oi.espec_pneu, oi.marca_pneu, 
       oi.categoria, oi.sistema
FROM ordens_servico os
LEFT JOIN os_itens oi ON oi.os_id = os.id
WHERE os.numero_os IN ('OS-2025-0026', 'OS-2026-0217')
ORDER BY os.numero_os, oi.posicao_pneu
""").fetchall()
print("=== OS itens ===")
for r in os_rows:
    print(r)

# Check rodizios for MAX4116
rod_rows = conn.execute("""
SELECT * FROM pneu_rodizios WHERE placa = 'MAX4116'
""").fetchall()
print("\n=== Rodizios MAX4116 ===")
for r in rod_rows:
    print(r)

# Check espec_pneu on OS-2025-0026 os_items
items_0026 = conn.execute("""
SELECT oi.id, oi.posicao_pneu, oi.espec_pneu, oi.marca_pneu, oi.qtd_pneu, oi.categoria, oi.sistema, oi.manejo_pneu
FROM ordens_servico os
JOIN os_itens oi ON oi.os_id = os.id
WHERE os.numero_os = 'OS-2025-0026'
""").fetchall()
print("\n=== Itens OS-2025-0026 ===")
for r in items_0026:
    print(r)

items_0217 = conn.execute("""
SELECT oi.id, oi.posicao_pneu, oi.espec_pneu, oi.marca_pneu, oi.qtd_pneu, oi.categoria, oi.sistema, oi.manejo_pneu
FROM ordens_servico os
JOIN os_itens oi ON oi.os_id = os.id
WHERE os.numero_os = 'OS-2026-0217'
""").fetchall()
print("\n=== Itens OS-2026-0217 ===")
for r in items_0217:
    print(r)

conn.close()
