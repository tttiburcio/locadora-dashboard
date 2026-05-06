import sqlite3
from pathlib import Path

db_path = Path('locadora.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- NOTAS FISCAIS ---")
cursor.execute("SELECT id, numero_nf, os_id, valor_total_nf FROM notas_fiscais WHERE numero_nf = '923535'")
nfs = cursor.fetchall()
for nf in nfs:
    print(nf)
    nf_id = nf[0]
    print(f"  Parcelas vinculadas à NF ID {nf_id}:")
    cursor.execute("SELECT id, parcela_atual, parcela_total, data_vencimento, valor_parcela FROM manutencao_parcelas WHERE nf_id = ?", (nf_id,))
    ps = cursor.fetchall()
    for p in ps:
        print(f"    {p}")

print("\n--- PARCELAS SEM NF_ID (LEGADO) ---")
cursor.execute("SELECT id, nota, parcela_atual, parcela_total, data_vencimento, valor_parcela FROM manutencao_parcelas WHERE nota = '923535' AND nf_id IS NULL")
ps_orfas = cursor.fetchall()
for p in ps_orfas:
    print(p)

conn.close()
