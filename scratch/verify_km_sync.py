import sys, io, sqlite3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

conn = sqlite3.connect("locadora.db")
cur = conn.cursor()

cur.execute("SELECT id FROM frota WHERE placa = 'DYG5G03'")
vid = cur.fetchone()[0]

print("=== manutencoes (DYG5G03) ===")
cur.execute(
    "SELECT id_ord_serv, data_execucao, data_entrada, km FROM manutencoes "
    "WHERE id_veiculo = ? ORDER BY COALESCE(data_execucao, data_entrada)",
    (vid,)
)
for row in cur.fetchall():
    print(f"  {row[0]:20s} | exec={row[1]} | entrada={row[2]} | km={row[3]}")

print("\n=== ordens_servico (DYG5G03) ===")
cur.execute(
    "SELECT numero_os, data_execucao, data_entrada, km FROM ordens_servico "
    "WHERE id_veiculo = ? ORDER BY COALESCE(data_execucao, data_entrada)",
    (vid,)
)
for row in cur.fetchall():
    print(f"  {row[0]:20s} | exec={row[1]} | entrada={row[2]} | km={row[3]}")

conn.close()
