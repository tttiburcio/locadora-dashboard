import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT numero_os, deletado_em FROM ordens_servico WHERE numero_os = 'OS-2026-0214'")
print("Deletado state:", cur.fetchone())
conn.close()
