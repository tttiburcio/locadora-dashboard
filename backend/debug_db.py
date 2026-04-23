import sqlite3
from pathlib import Path
DB_PATH = Path(__file__).parent.parent / "locadora.db"
if not DB_PATH.exists():
    print("DB not found")
else:
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    print("--- VEHICLE ---")
    res = cursor.execute("SELECT id, placa FROM frota WHERE placa = 'EXW7D65'").fetchall()
    print(res)
    if res:
        vid = res[0][0]
        print(f"\n--- OS FOR VEHICLE {vid} ---")
        os_list = cursor.execute("SELECT id, numero_os, status_os, data_execucao, total_os FROM ordens_servico WHERE id_veiculo = ?", (vid,)).fetchall()
        for o in os_list:
            print(o)
    conn.close()
