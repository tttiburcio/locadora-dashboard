import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT strftime('%Y', '2026-05-09')")
print("Literal test:", cur.fetchone())
cur.execute("SELECT strftime('%Y', COALESCE(data_execucao, data_entrada)) FROM ordens_servico WHERE numero_os = 'OS-2026-0214'")
print("Column value test:", cur.fetchone())
conn.close()
