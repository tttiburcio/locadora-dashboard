import sys
import pandas as pd
from sqlalchemy import text

sys.path.append(r'c:\Users\ADM\Documents\locadora-dashboard\backend')
from main import load_raw, _filter_year, _parse, _dedup_manut, engine

def audit_dtypes():
    data = load_raw()
    frota = data["frota"].copy()
    manut_raw = _filter_year(_parse(data["manutencoes"].copy(), "DataExecução"), "DataExecução", 2026)
    
    with engine.connect() as conn:
        sql_frota = pd.read_sql("SELECT id as IDVeiculo, placa as Placa FROM frota", conn)
        sql_os = pd.read_sql(text("""
                SELECT os.id as id_sql, os.id_veiculo as IDVeiculo, os.placa as Placa,
                       COALESCE(os.data_execucao, os.data_entrada) as DataExecução,
                       100 as TotalOS, os.numero_os as IDOrdServ
                FROM ordens_servico os
        """), conn)
    
    # Simulating frota creation logic from main.py
    frota = pd.concat([frota, sql_frota], ignore_index=True).drop_duplicates(subset=["Placa"], keep="last")
    
    # Simulating manut creation
    manut_raw = pd.concat([manut_raw, sql_os], ignore_index=True)
    manut = _dedup_manut(manut_raw)
    
    print("--- DTYPE AUDIT ---")
    print(f"frota['IDVeiculo'] dtype: {frota['IDVeiculo'].dtype}")
    print(f"manut['IDVeiculo'] dtype: {manut['IDVeiculo'].dtype}")
    
    c_manut = manut.dropna(subset=["IDVeiculo"]).groupby("IDVeiculo")["TotalOS"].sum().rename("CustoManutencao")
    print(f"c_manut.index.dtype: {c_manut.index.dtype}")
    
    # Try join
    base_cols = ["IDVeiculo", "Placa"]
    test_df = frota[base_cols].set_index("IDVeiculo").join(c_manut, how="left")
    
    # Count items successfully joined
    joined_count = test_df['CustoManutencao'].notna().sum()
    print(f"Successfully joined items: {joined_count} / {len(c_manut)}")
    
    if joined_count == 0 and len(c_manut) > 0:
        print("CRITICAL FAILURE: JOIN FAILED COMPLETELY DUE TO TYPE MISMATCH!")
    
audit_dtypes()
