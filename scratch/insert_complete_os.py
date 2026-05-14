import sqlite3
from datetime import datetime

conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

try:
    print("Beginning database transaction retry...")
    now_str = datetime.now().isoformat()

    # 1. Insert Ordens Servico
    cur.execute("""
        INSERT INTO ordens_servico (
            numero_os, status_os, id_veiculo, placa, modelo, implemento, fornecedor, fornecedor_id, 
            total_os, km, data_entrada, data_execucao, tipo_manutencao, categoria, criado_em, origem
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'OS-2025-0147', 'finalizada', 43, 'CSU3F94', 'Express Delivery', 'Carroceria', 'GP PNEUS', 33,
        2200.00, 63352.47, '2025-12-18', '2025-12-18', 'Corretiva', 'Compra', now_str, 'manual'
    ))
    os_id = cur.lastrowid
    print(f"Inserted OS, ID={os_id}")

    # 2. Insert Item
    cur.execute("""
        INSERT INTO os_itens (
            os_id, categoria, sistema, servico, descricao, qtd_itens, posicao_pneu, qtd_pneu,
            espec_pneu, marca_pneu, modelo_pneu, condicao_pneu, manejo_pneu, criado_em, fornecedor_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        os_id, 'Compra', 'Pneu', 'FORNECIMENTO DE PNEUS', 'FORNECIMENTO: 02 PNEUS 225/75R16C GENERAL EUROVAN TRASEIROS',
        '02 PNEUS', 'TRASEIRO', 2.0, '225/75r16c', 'CONTINENTAL', 'GENERAL EUROVAN', 'NOVO', 'Loja', now_str, 33
    ))
    item_id = cur.lastrowid
    print(f"Inserted OS Item, ID={item_id}")

    # 3. Insert Nota Fiscal
    cur.execute("""
        INSERT INTO notas_fiscais (
            os_id, numero_nf, fornecedor, valor_total_nf, data_emissao, criado_em, tipo_nf
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        os_id, '63034', 'GP PNEUS', 2200.00, '2025-12-18', now_str, 'Produto'
    ))
    nf_id = cur.lastrowid
    print(f"Inserted Nota Fiscal, ID={nf_id}")

    # 4. Insert 3 Parcelas
    parcela_data = [
        ('2026-01-19', 733.33),
        ('2026-02-18', 733.33),
        ('2026-03-18', 733.34),
    ]
    
    for i, (d_venc, val) in enumerate(parcela_data):
        cur.execute("""
            INSERT INTO manutencao_parcelas (
                manutencao_id, nf_id, nota, fornecedor, valor_item_total,
                parcela_atual, parcela_total, valor_parcela, status_pagamento,
                data_vencimento, data_vencimento_original
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            os_id, nf_id, '63034', 'GP PNEUS', 2200.00,
            i+1, 3, val, 'Pago',
            d_venc, d_venc
        ))
        print(f"Inserted Parcela {i+1}/{3} with status Paid.")

    conn.commit()
    print("TRANSACTION COMMITTED SUCCESSFULLY.")
except Exception as e:
    conn.rollback()
    print("TRANSACTION FAILED AND ROLLED BACK.")
    print("Error:", e)

conn.close()
