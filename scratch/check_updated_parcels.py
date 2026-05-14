import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("""
    SELECT os.numero_os, os.placa, p.id, p.valor_parcela, p.valor_atualizado 
    FROM manutencao_parcelas p
    JOIN notas_fiscais nf ON nf.id = p.nf_id
    JOIN ordens_servico os ON os.id = nf.os_id
    WHERE p.valor_atualizado IS NOT NULL AND p.valor_atualizado > 0
""")
print("Parcelas with modified 'valor_atualizado':")
for r in cur.fetchall():
    print(r)
conn.close()
