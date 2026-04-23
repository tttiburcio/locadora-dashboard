import sqlite3
import json

def check_vehicle_os(placa):
    conn = sqlite3.connect('locadora.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, numero_os, status_os, data_execucao, total_os, data_entrada FROM ordens_servico WHERE placa = ? AND deletado_em IS NULL", (placa,))
    rows = [dict(r) for r in cur.fetchall()]
    print(f"OS for {placa}:")
    print(json.dumps(rows, indent=2))
    conn.close()

if __name__ == "__main__":
    check_vehicle_os("DPB8E26")
