import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT id, numero_os, total_os, data_execucao, data_entrada FROM ordens_servico WHERE numero_os = 'OS-2026-0201'")
print("DB state for OS-2026-0201:", cur.fetchone())
conn.close()
