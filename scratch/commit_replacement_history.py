import sqlite3
from datetime import datetime

conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

try:
    print("Beginning Replacement OS Transaction...")
    
    # 1. Increment OS Counter to 216
    cur.execute("UPDATE os_counters SET ultimo = 216 WHERE ano = 2026")
    print("Incremented OS Counter for 2026 to 216.")
    
    now_str = datetime.now().isoformat()
    os_num = 'OS-2026-0216'
    
    # Details derived from lookups
    plate = 'CSU3F94'
    v_id = 43
    model = 'Express Delivery'
    impl = 'Carroceria'
    comp_id = '3' # String '3' consistent with reconciliation
    cont_id = 29
    final_km = 64895.66
    exec_date = '2026-01-16'
    obs = "Substituição de 01 unidade pneu dianteiro realizada pela empresa locatária (sem custo direto cadastrado) para repor pneu original da OS-2025-0112, que estourou em queda em buraco ocorrida em 06/01/2026 (KM referencial do incidente: 64.189,21 km)."
    
    # 2. Insert the OS record
    cur.execute("""
        INSERT INTO ordens_servico (
            numero_os, status_os, id_veiculo, placa, modelo, implemento, empresa, id_contrato,
            total_os, km, data_entrada, data_execucao, tipo_manutencao, categoria, observacoes, criado_em, origem
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        os_num, 'finalizada', v_id, plate, model, impl, comp_id, cont_id,
        0.0, final_km, exec_date, exec_date, 'Corretiva', 'Compra', obs, now_str, 'manual'
    ))
    
    os_id = cur.lastrowid
    print(f"Inserted {os_num}, internal ID={os_id}")
    
    # 3. Insert the specific OS Item for the GOODYEAR Pneu
    cur.execute("""
        INSERT INTO os_itens (
            os_id, categoria, sistema, servico, descricao, qtd_itens, posicao_pneu, qtd_pneu,
            espec_pneu, marca_pneu, modelo_pneu, condicao_pneu, manejo_pneu, criado_em
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        os_id, 'Compra', 'Pneu', 'FORNECIMENTO DE PNEUS', '01 PNEU 225/75R16C GOODYEAR CARGO MARATHON REPOSIÇÃO',
        1, 'DIANTEIRO', 1, '225/75R16C', 'GOODYEAR', 'CARGO MARATHON', 'NOVO', 'Loja', now_str
    ))
    
    print("Inserted Goodyear Pneu record successfully.")
    
    conn.commit()
    print("\nTRANSACTION COMMITTED SUCCESSFULLY!")
    
except Exception as e:
    conn.rollback()
    print("\nTRANSACTION FAILED AND ROLLED BACK.")
    print("Error Details:", e)

conn.close()
