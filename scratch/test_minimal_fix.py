import sys
import pandas as pd
from sqlalchemy import text

sys.path.append(r'c:\Users\ADM\Documents\locadora-dashboard\backend')
from main import engine

def get_baseline_manut(year):
    with engine.connect() as conn:
        # EXISTING logic currently live
        sql_os = pd.read_sql(text("""
                SELECT os.id, os.placa,
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
                       END as TotalOS
                FROM ordens_servico os
                WHERE os.deletado_em IS NULL
        """), conn, params={"year": str(year)})
    return sql_os

def get_proposed_manut(year):
    with engine.connect() as conn:
        # SAME logic, BUT ADDING valor_atualizado support
        sql_os = pd.read_sql(text("""
                SELECT os.id, os.placa,
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
                              AND nf.deletado_em IS NULL
                              AND strftime('%Y', p.data_vencimento) = :year),
                           0
                         )
                         ELSE COALESCE(os.total_os, (SELECT SUM(valor_total_nf) FROM notas_fiscais WHERE os_id = os.id AND deletado_em IS NULL), 0)
                       END as TotalOS
                FROM ordens_servico os
                WHERE os.deletado_em IS NULL
        """), conn, params={"year": str(year)})
    return sql_os

base = get_baseline_manut(2026).groupby('placa')['TotalOS'].sum()
prop = get_proposed_manut(2026).groupby('placa')['TotalOS'].sum()

diff = prop - base
changed = diff[diff > 0.01]
print("\nVEHICLES THAT GAIN VALUE JUST FROM valor_atualizado FIX:")
print(changed)
