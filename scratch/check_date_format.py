import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT numero_os, data_execucao, data_entrada FROM ordens_servico WHERE numero_os = 'OS-2026-0214'")
print("Dates for OS-2026-0214:", cur.fetchone())
conn.close()
