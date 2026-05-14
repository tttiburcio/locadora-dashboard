import sys
import pandas as pd
from sqlalchemy import text

sys.path.append(r'c:\Users\ADM\Documents\locadora-dashboard\backend')
from main import load_raw, _filter_year, _parse, _dedup_manut, engine

def get_baseline_manut(year):
    data = load_raw()
    manut_raw = _filter_year(_parse(data["manutencoes"].copy(), "DataExecução"), "DataExecução", year)
    
    with engine.connect() as conn:
        # Exact copy of the EXISTING query from backend/main.py
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
                              AND strftime('%Y', p.data_vencimento) = :year),
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
                        AND strftime('%Y', p.data_vencimento) = :year
                    )
                    OR strftime('%Y', COALESCE(os.data_execucao, os.data_entrada)) = :year
                  )
        """), conn, params={"year": str(year)})
        
    sql_os["DataExecução"] = pd.to_datetime(sql_os["DataExecução"])
    if not manut_raw.empty and "IDOrdServ" in manut_raw.columns:
        sql_ids = set(sql_os["IDOrdServ"].dropna().unique())
        manut_raw = manut_raw[~manut_raw["IDOrdServ"].isin(sql_ids)]
    manut_raw = pd.concat([manut_raw, sql_os], ignore_index=True)
    manut = _dedup_manut(manut_raw)
    return manut.dropna(subset=["IDVeiculo"]).groupby("Placa")["TotalOS"].sum()

def get_proposed_manut(year):
    data = load_raw()
    manut_raw = _filter_year(_parse(data["manutencoes"].copy(), "DataExecução"), "DataExecução", year)
    
    with engine.connect() as conn:
        # My proposed Accrual Based query incorporating COALESCE(valor_atualizado, valor_parcela)
        sql_os = pd.read_sql(text("""
                SELECT os.id as id_sql, os.id_veiculo as IDVeiculo, os.placa as Placa,
                       COALESCE(
                           os.data_execucao, 
                           os.data_entrada,
                           (SELECT MIN(p.data_vencimento) FROM manutencao_parcelas p JOIN notas_fiscais nf ON nf.id=p.nf_id WHERE nf.os_id=os.id AND p.deletado_em IS NULL)
                       ) as DataExecução,
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
                       END as TotalOS,
                       os.numero_os as IDOrdServ
                FROM ordens_servico os
                WHERE os.deletado_em IS NULL
                  AND strftime('%Y', COALESCE(
                      os.data_execucao, 
                      os.data_entrada,
                      (SELECT MIN(p.data_vencimento) FROM manutencao_parcelas p JOIN notas_fiscais nf ON nf.id=p.nf_id WHERE nf.os_id=os.id AND p.deletado_em IS NULL)
                  )) = :year
        """), conn, params={"year": str(year)})
        
    sql_os["DataExecução"] = pd.to_datetime(sql_os["DataExecução"])
    if not manut_raw.empty and "IDOrdServ" in manut_raw.columns:
        sql_ids = set(sql_os["IDOrdServ"].dropna().unique())
        manut_raw = manut_raw[~manut_raw["IDOrdServ"].isin(sql_ids)]
    manut_raw = pd.concat([manut_raw, sql_os], ignore_index=True)
    manut = _dedup_manut(manut_raw)
    return manut.dropna(subset=["IDVeiculo"]).groupby("Placa")["TotalOS"].sum()

# Execution and Diff
base = get_baseline_manut(2026)
prop = get_proposed_manut(2026)

print("\nDIFF REPORT FOR YEAR 2026 (Accrual Proposed vs Current Cashflow Split):")
print(f"{'Placa':<10} | {'Current Val':<15} | {'Proposed Val':<15} | {'DIFF':<15}")
print("-" * 60)

all_placas = sorted(list(set(base.index) | set(prop.index)))
for p in all_placas:
    bv = base.get(p, 0)
    pv = prop.get(p, 0)
    d = pv - bv
    if abs(d) > 0.01:
        print(f"{p:<10} | {bv:<15.2f} | {pv:<15.2f} | {d:<15.2f}")

print("\nTotal Delta across all vehicles:", prop.sum() - base.sum())
