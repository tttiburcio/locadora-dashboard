import os
import sys
import pandas as pd
from sqlalchemy import text

sys.path.append(r'c:\Users\ADM\Documents\locadora-dashboard\backend')

from main import load_raw, _filter_year, _parse, _dedup_manut, engine

def debug_compute_step():
    data = load_raw()
    manut_raw = _filter_year(_parse(data["manutencoes"].copy(), "DataExecução"), "DataExecução", 2026)
    
    with engine.connect() as conn:
        sql_os = pd.read_sql(text("""
                SELECT os.id as id_sql, os.id_veiculo as IDVeiculo, os.placa as Placa,
                       COALESCE(os.data_execucao, os.data_entrada) as DataExecução,
                       CASE
                         WHEN EXISTS (
                           SELECT 1 FROM notas_fiscais nf
                           JOIN manutencao_parcelas p ON p.nf_id = nf.id
                           WHERE nf.os_id = os.id AND nf.deletado_em IS NULL AND p.deletado_em IS NULL
                         )
                         THEN COALESCE(
                           (SELECT SUM(p.valor_parcela)
                            FROM manutencao_parcelas p
                            JOIN notas_fiscais nf ON nf.id = p.nf_id
                            WHERE nf.os_id = os.id
                              AND p.deletado_em IS NULL
                              AND nf.deletado_em IS NULL
                              AND strftime('%Y', p.data_vencimento) = '2026'),
                           0
                         )
                         ELSE COALESCE(os.total_os, (SELECT SUM(valor_total_nf) FROM notas_fiscais WHERE os_id = os.id AND deletado_em IS NULL), 0)
                       END as TotalOS,
                       os.numero_os as IDOrdServ
                FROM ordens_servico os
                WHERE os.deletado_em IS NULL
                  AND (
                    EXISTS (
                      SELECT 1 FROM notas_fiscais nf
                      JOIN manutencao_parcelas p ON p.nf_id = nf.id
                      WHERE nf.os_id = os.id AND nf.deletado_em IS NULL AND p.deletado_em IS NULL
                        AND strftime('%Y', p.data_vencimento) = '2026'
                    )
                    OR strftime('%Y', COALESCE(os.data_execucao, os.data_entrada)) = '2026'
                  )
        """), conn)
        
    sql_os["DataExecução"] = pd.to_datetime(sql_os["DataExecução"])
    if not manut_raw.empty and "IDOrdServ" in manut_raw.columns:
        sql_ids = set(sql_os["IDOrdServ"].dropna().unique())
        manut_raw = manut_raw[~manut_raw["IDOrdServ"].isin(sql_ids)]
    manut_raw = pd.concat([manut_raw, sql_os], ignore_index=True)
    
    manut = _dedup_manut(manut_raw)
    
    relevant = manut[manut['Placa'] == 'EVF8I83']
    print("\nDetailed entries summed for EVF8I83 CustoManutencao:")
    print(relevant[['IDOrdServ', 'TotalOS', 'DataExecução']])
    print("\nSUM of TotalOS for EVF8I83:", relevant['TotalOS'].sum())

debug_compute_step()
