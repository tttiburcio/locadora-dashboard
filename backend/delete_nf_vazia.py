import sqlite3

DB = r'C:\Users\vinic\Documents\clone\locadora.db'
conn = sqlite3.connect(DB)

# Delete parcelas linked to NF id=260 (table is manutencao_parcelas)
deleted_parcelas = conn.execute("DELETE FROM manutencao_parcelas WHERE nf_id = 260").rowcount
deleted_itens    = conn.execute("DELETE FROM nf_itens WHERE nf_id = 260").rowcount
deleted_nf       = conn.execute("DELETE FROM notas_fiscais WHERE id = 260").rowcount
conn.commit()

print(f"Deleted: {deleted_parcelas} parcelas, {deleted_itens} nf_itens, {deleted_nf} NF")

# Verify remaining NFs for OS-2026-0203 (os_id=201)
remaining = conn.execute("SELECT id, numero_nf, fornecedor, empresa_faturada, valor_total_nf FROM notas_fiscais WHERE os_id = 201").fetchall()
print("NFs restantes:")
for r in remaining:
    print(" ", r)

conn.close()
