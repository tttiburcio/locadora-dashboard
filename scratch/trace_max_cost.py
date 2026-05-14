import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

# Look at ALL ordens of MAX4116 not deleted
cur.execute("""
    SELECT os.id, os.numero_os, os.total_os, os.data_execucao
    FROM ordens_servico os
    WHERE os.placa = 'MAX4116' AND os.deletado_em IS NULL
""")
print("All active OS for MAX4116:")
for r in cur.fetchall():
    print(r)
    
    # Also print its installments
    subcur = conn.cursor()
    subcur.execute("""
        SELECT p.id, p.data_vencimento, p.valor_parcela
        FROM manutencao_parcelas p
        JOIN notas_fiscais nf ON nf.id = p.nf_id
        WHERE nf.os_id = ? AND p.deletado_em IS NULL
    """, (r[0],))
    print("  --> Installments:")
    for ir in subcur.fetchall():
        print("     ", ir)

conn.close()
