import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

print("Verifying categories for newly created OS-2025-0147:")
cur.execute("SELECT categoria FROM ordens_servico WHERE numero_os = 'OS-2025-0147'")
print("  OS Category:", cur.fetchone()[0])

cur.execute("""
    SELECT oi.categoria 
    FROM os_itens oi 
    JOIN ordens_servico os ON os.id = oi.os_id 
    WHERE os.numero_os = 'OS-2025-0147'
""")
print("  Item Category:", cur.fetchone()[0])

conn.close()
