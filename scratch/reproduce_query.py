import pandas as pd
import numpy as np
from pathlib import Path
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///locadora.db")

def test_os_query(year):
    query = """
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
                      AND strftime('%Y', p.data_vencimento) = :year),
                   0
                 )
                 ELSE COALESCE(os.total_os, (SELECT SUM(valor_total_nf) FROM notas_fiscais WHERE os_id = os.id AND deletado_em IS NULL), 0)
               END as TotalOS,
               os.fornecedor as Fornecedor, os.modelo as Modelo, os.numero_os as IDOrdServ
        FROM ordens_servico os
        WHERE os.deletado_em IS NULL
          AND (
            EXISTS (
              SELECT 1 FROM notas_fiscais nf
              JOIN manutencao_parcelas p ON p.nf_id = nf.id
              WHERE nf.os_id = os.id AND nf.deletado_em IS NULL AND p.deletado_em IS NULL
                AND strftime('%Y', p.data_vencimento) = :year
            )
            OR strftime('%Y', COALESCE(os.data_execucao, os.data_entrada)) = :year
          )
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params={"year": str(year)})
    return df

print("--- Query Output for 2026 ---")
res = test_os_query(2026)
print(res[res['Placa'].isin(['EVF8I83', 'MAX4116'])][['IDOrdServ', 'Placa', 'TotalOS', 'DataExecução']])
