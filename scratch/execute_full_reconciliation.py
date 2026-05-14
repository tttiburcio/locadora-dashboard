import sqlite3

conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

def normalize_empresa(raw):
    if raw is None: return None
    raw = str(raw).strip().upper()
    if raw in ('1', '1.0', 'TKJ'): return '1'
    if raw in ('2', '2.0', 'FINITA'): return '2'
    if raw in ('3', '3.0', 'LANDKRAFT'): return '3'
    return None

try:
    print("Starting Total Reconciliation Transaction...")
    
    # --- PART 1: Normalize Notas Fiscais column formats ---
    cur.execute("SELECT id, empresa_faturada FROM notas_fiscais")
    nfs = cur.fetchall()
    nf_fixes = 0
    for nid, ef in nfs:
        n = normalize_empresa(ef)
        if n is not None and n != str(ef):
            cur.execute("UPDATE notas_fiscais SET empresa_faturada = ? WHERE id = ?", (n, nid))
            nf_fixes += 1
    print(f"  -> Step 1 complete: Cleaned {nf_fixes} entries in 'notas_fiscais'.")

    # --- PART 2: Reconcile Ordens Servico links ---
    cur.execute("""
        SELECT id, id_veiculo, COALESCE(data_execucao, data_entrada) as dt, empresa, id_contrato
        FROM ordens_servico
    """)
    oss = cur.fetchall()
    
    os_fixes = 0
    for os_id, id_v, dt, old_e, old_c in oss:
        # A. Determine Active Contract at Execution time
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
                ORDER BY c.data_inicio DESC LIMIT 1
            """, (id_v, dt_str, dt_str))
            row = cur.fetchone()
            if row:
                active_c_id, active_e_id = row
                # Convert integer 1 to string '1'
                if active_e_id: active_e_id = str(int(active_e_id))

        # B. Determine Final Correct Empresa
        inv_e = None
        cur.execute("SELECT empresa_faturada FROM notas_fiscais WHERE os_id = ? AND deletado_em IS NULL LIMIT 1", (os_id,))
        row2 = cur.fetchone()
        if row2 and row2[0]:
            inv_e = normalize_empresa(row2[0])
            
        # Final calculation of truths
        final_emp = inv_e or active_e_id or normalize_empresa(old_e)
        final_con = active_c_id
        
        # Build actual current values to compare
        clean_old_e = normalize_empresa(old_e)
        
        # Check if something NEEDS updating to trigger write
        e_diff = final_emp and final_emp != clean_old_e
        c_diff = final_con and final_con != old_c
        
        # Wait! ALWAYS overwrite string versions like "1.0" into "1" EVEN IF logic is same
        if final_emp and final_emp != str(old_e):
             e_diff = True

        if e_diff or c_diff:
            # Map values, keeping existing if final deduces null somehow
            set_emp = final_emp if final_emp else old_e
            set_con = final_con if final_con else old_c
            
            cur.execute("UPDATE ordens_servico SET empresa = ?, id_contrato = ? WHERE id = ?", 
                        (set_emp, set_con, os_id))
            os_fixes += 1

    print(f"  -> Step 2 complete: Fixed relational integrity for {os_fixes} 'ordens_servico'.")
    
    conn.commit()
    print("\nCOMMIT SUCCESS: Total system sanitization complete.")

except Exception as e:
    conn.rollback()
    print("\nFAIL: Transaction rolled back. Error:", e)

conn.close()
