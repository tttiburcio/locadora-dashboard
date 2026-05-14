import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

# Check notas
cur.execute("""
    SELECT id, numero_nf, valor_total_nf, deletado_em
    FROM notas_fiscais
    WHERE os_id = 203
""")
print("Notas for OS-2026-0205:")
for r in cur.fetchall():
    print(r)

# Check parcelas
cur.execute("""
    SELECT p.id, p.valor_parcela, p.data_vencimento, p.deletado_em
    FROM manutencao_parcelas p
    JOIN notas_fiscais nf ON nf.id = p.nf_id
    WHERE nf.os_id = 203
""")
print("\nParcelas for OS-2026-0205:")
for r in cur.fetchall():
    print(r)

conn.close()
