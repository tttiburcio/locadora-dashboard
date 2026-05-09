import sqlite3
import os

# Try different db paths
for dbpath in ["locadora.db", "backend/locadora.db"]:
    if os.path.exists(dbpath):
        print(f"\n=== {dbpath} ===")
        conn = sqlite3.connect(dbpath)
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        print("Tables:", tables)

        if "frota" in tables:
            cur.execute("SELECT id, placa, modelo FROM frota WHERE placa = 'DYG5G03'")
            frota = cur.fetchall()
            print("FROTA:", frota)

            if frota:
                vid = frota[0][0]
                cur.execute(
                    "SELECT id, id_ord_serv, data_execucao, data_entrada, km "
                    "FROM manutencoes WHERE id_veiculo = ? ORDER BY data_execucao",
                    (vid,)
                )
                rows = cur.fetchall()
                print(f"\nTotal manutencoes: {len(rows)}")
                for r in rows:
                    print(r)

                if "ordens_servico" in tables:
                    cur.execute(
                        "SELECT id, numero_os, data_execucao, data_entrada, km "
                        "FROM ordens_servico WHERE id_veiculo = ? ORDER BY data_execucao",
                        (vid,)
                    )
                    os_rows = cur.fetchall()
                    print(f"\nTotal ordens_servico: {len(os_rows)}")
                    for r in os_rows:
                        print(r)
        conn.close()
