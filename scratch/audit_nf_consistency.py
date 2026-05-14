import sqlite3

conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

def normalize_empresa(raw):
    if raw is None: return None
    raw = str(raw).strip().upper()
    if raw in ('1', '1.0', 'TKJ'): return '1'
    if raw in ('2', '2.0', 'FINITA'): return '2'
    if raw in ('3', '3.0', 'LANDKRAFT'): return '3'
    return raw

cur.execute("SELECT id, empresa_faturada FROM notas_fiscais WHERE deletado_em IS NULL")
nf_rows = cur.fetchall()
nf_updates = []
for nid, ef in nf_rows:
    norm = normalize_empresa(ef)
    if norm != str(ef) and norm is not None:
         nf_updates.append((norm, nid))

print(f"Preparing {len(nf_updates)} updates for Notas Fiscais consistency.")
conn.close()
