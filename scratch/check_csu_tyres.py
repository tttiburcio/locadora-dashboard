import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

print("Checking recent OS Items for Pneu system (CSU3F94):")
cur.execute("""
    SELECT os.numero_os, COALESCE(os.data_execucao, os.data_entrada) as data, 
           oi.posicao_pneu, oi.marca_pneu, oi.modelo_pneu, oi.espec_pneu, oi.condicao_pneu, oi.manejo_pneu, oi.qtd_pneu
    FROM os_itens oi
    JOIN ordens_servico os ON os.id = oi.os_id
    WHERE os.placa = 'CSU3F94' AND LOWER(oi.sistema) = 'pneu' AND os.deletado_em IS NULL
    ORDER BY data DESC
""")
for r in cur.fetchall():
    print(" ", r)

print("\nChecking Pneu Rodizios (CSU3F94):")
cur.execute("""
    SELECT data, km, posicao_anterior, posicao_nova, espec_pneu, marca_pneu, qtd
    FROM pneu_rodizios
    WHERE placa = 'CSU3F94'
    ORDER BY data DESC
""")
for r in cur.fetchall():
    print(" ", r)

conn.close()
