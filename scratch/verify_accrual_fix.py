import pandas as pd
import sqlite3
import urllib.request
import json

def get_proposed_totals(year):
    conn = sqlite3.connect('locadora.db')
    # Implementing the proposed robust SQL override query
    query = f"""
        SELECT os.id_veiculo as IDVeiculo,
               COALESCE(os.data_execucao, os.data_entrada, 
                        (SELECT MIN(p.data_vencimento) 
                         FROM manutencao_parcelas p 
                         JOIN notas_fiscais nf ON nf.id = p.nf_id 
                         WHERE nf.os_id = os.id AND p.deletado_em IS NULL AND nf.deletado_em IS NULL)
               ) as DataExecucao,
               CASE
                 WHEN EXISTS (
                   SELECT 1 FROM notas_fiscais nf
                   JOIN manutencao_parcelas p ON p.nf_id = nf.id
                   WHERE nf.os_id = os.id AND nf.deletado_em IS NULL AND p.deletado_em IS NULL
                 )
                 THEN COALESCE(
                   (SELECT SUM(COALESCE(p.valor_atualizado, p.valor_parcela))
                    FROM manutencao_parcelas p
                    JOIN notas_fiscais nf ON nf.id = p.nf_id
                    WHERE nf.os_id = os.id
                      AND p.deletado_em IS NULL
                      AND nf.deletado_em IS NULL),
                   0
                 )
                 ELSE COALESCE(os.total_os, (SELECT SUM(valor_total_nf) FROM notas_fiscais WHERE os_id = os.id AND deletado_em IS NULL), 0)
               END as TotalOS
        FROM ordens_servico os
        WHERE os.deletado_em IS NULL
    """
    df_all = pd.read_sql(query, conn)
    conn.close()
    
    # Filter outside SQL to replicate strftime filter on calculated DataExecucao
    df_all['DataExecucao'] = pd.to_datetime(df_all['DataExecucao'], errors='coerce')
    df_2026 = df_all[df_all['DataExecucao'].dt.year == year]
    
    return df_2026.groupby('IDVeiculo')['TotalOS'].sum()

try:
    # 1. Get CURRENT live totals from API
    with urllib.request.urlopen("http://localhost:8000/api/vehicles?year=2026") as r:
        live_data = json.loads(r.read().decode())
    live_vehicles = {v['id']: (v['placa'], v['custo_manutencao']) for v in live_data['vehicles']}

    # 2. Get totals with the proposed Accrual fix
    # (We only calculate SQL contribution because Excel stays exact same)
    proposed = get_proposed_totals(2026)
    
    print("AUDIT OF ACCRUAL FIX IMPACT ON VEHICLES:")
    
    # Since my proposed script ONLY pulls SQL, I need to also grab existing vehicle ids to show compare.
    # Actually, let's just run a script that DOES the COMPLETE compute override and compares it
    pass
except Exception as e:
    print("Error setup:", e)

conn = sqlite3.connect('locadora.db')
cur = conn.cursor()
cur.execute("SELECT id, placa FROM frota")
placa_map = {r[0]: r[1] for r in cur.fetchall()}
conn.close()

proposed = get_proposed_totals(2026)
print("\nProposed SQL Full-Accrual Totals by Vehicle (2026):")
for vid, tot in proposed.items():
    print(f"Vehicle {vid} ({placa_map.get(vid, 'Unknown')}): Proposed SQL contribution = {tot}")
