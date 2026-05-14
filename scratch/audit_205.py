import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

# Check items
cur.execute("""
    SELECT id, sistema, servico, valor_unitario, quantidade, valor_total
    FROM os_itens
    WHERE os_id = 203
""")
print("Items for OS-2026-0205 (ID 203):")
for r in cur.fetchall():
    print(r)

# Check parcelas
cur.execute("""
    SELECT id, valor_parcela, data_vencimento
    FROM manutencao_parcelas p
    JOIN notas_fiscais nf ON nf.id = p.nf_id
    WHERE nf.os_id = 203
""")
print("\nParcelas for OS-2026-0205:")
for r in cur.fetchall():
    print(r)

# Also check if there's a total specified on OS itself
cur.execute("SELECT total_os FROM ordens_servico WHERE id = 203")
print("\nTotal stored on OS:", cur.fetchone())

conn.close()
