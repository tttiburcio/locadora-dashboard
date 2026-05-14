import sqlite3

conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

# Build cache for mapping non-standard company labels to ID
def normalize_empresa(raw):
    if raw is None: return None
    raw = str(raw).strip().upper()
    if raw in ('1', '1.0', 'TKJ'): return 1
    if raw in ('2', '2.0', 'FINITA'): return 2
    if raw in ('3', '3.0', 'LANDKRAFT'): return 3
    return None

# 1. Fetch all active OS
cur.execute("""
    SELECT id, numero_os, id_veiculo, COALESCE(data_execucao, data_entrada) as dt, empresa, id_contrato
    FROM ordens_servico
    WHERE deletado_em IS NULL
""")
oss = cur.fetchall()

updates = []

print(f"Auditing logic for {len(oss)} records...")
for os_id, os_num, id_v, dt, old_emp, old_con in oss:
    final_emp = None
    final_con = None
    
    # --- Step A: Look for active contract based on vehicle + date ---
    active_c_id = None
    active_e_id = None
    if id_v and dt:
        dt_str = str(dt)[:10]
        cur.execute("""
            SELECT c.id, c.empresa_id
            FROM contrato_veiculo cv
            JOIN contratos c ON c.id = cv.contrato_id
            WHERE cv.id_veiculo = ?
              AND (c.data_inicio IS NULL OR c.data_inicio <= ?)
              AND (c.data_encerramento IS NULL OR c.data_encerramento >= ?)
            ORDER BY c.data_inicio DESC
            LIMIT 1
        """, (id_v, dt_str, dt_str))
        c_row = cur.fetchone()
        if c_row:
            active_c_id, active_e_id = c_row

    # --- Step B: Look for explicit company override from Invoice ---
    inv_emp_id = None
    cur.execute("SELECT empresa_faturada FROM notas_fiscais WHERE os_id = ? AND deletado_em IS NULL LIMIT 1", (os_id,))
    i_row = cur.fetchone()
    if i_row and i_row[0]:
        inv_emp_id = normalize_empresa(i_row[0])

    # --- Step C: Consolidate ---
    # Rule for Empresa: 1st Priority is explicit Invoice, 2nd is Active Contract, 3rd is normalize current value
    final_emp = inv_emp_id or active_e_id or normalize_empresa(old_emp)
    
    # Rule for Contract
    final_con = active_c_id
    
    # Convert existing float/string formats into clean integers if possible
    curr_emp = normalize_empresa(old_emp)
    curr_con = old_con
    
    # Determine if update is needed
    needs_update = False
    if final_emp and str(curr_emp) != str(final_emp):
         needs_update = True
    if final_con and curr_con != final_con:
         needs_update = True
    
    if needs_update:
        updates.append((final_emp, final_con, os_id, f"Update OS {os_num}: Emp {old_emp}->{final_emp}, Con {old_con}->{final_con}"))

print(f"\nDRY RUN: {len(updates)} records scheduled for correction.")
for _, _, _, msg in updates[:15]:
    print(f"  - {msg}")
if len(updates) > 15:
    print("  ...")
conn.close()
