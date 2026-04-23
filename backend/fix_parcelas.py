import sqlite3
import os

db_path = r'c:\Users\vinic\Documents\clone\locadora.db'
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Get all NFs
cur.execute('SELECT id FROM notas_fiscais')
nfs = cur.fetchall()

print(f"Processing {len(nfs)} invoices...")

for (nf_id,) in nfs:
    cur.execute('SELECT id FROM manutencao_parcelas WHERE nf_id = ? ORDER BY data_vencimento, id', (nf_id,))
    parcs = cur.fetchall()
    total = len(parcs)
    if total == 0: continue
    
    for i, (p_id,) in enumerate(parcs):
        cur.execute('UPDATE manutencao_parcelas SET parcela_atual = ?, parcela_total = ? WHERE id = ?', (i+1, total, p_id))

conn.commit()
conn.close()
print("Done!")
