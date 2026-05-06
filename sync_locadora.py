import sqlite3
import pandas as pd
import numpy as np
import sys

# Ensure stdout handles UTF-8 correctly
if hasattr(sys.stdout, 'buffer'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

db_path = 'locadora.db'
xlsx_path = 'Locadora.xlsx'

def sync():
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = OFF")
    
    xl = pd.ExcelFile(xlsx_path)
    sheet_names = xl.sheet_names
    print(f"Total Sheets in Excel: {len(sheet_names)}")
    
    def find_sheet(keyword):
        return next((s for s in sheet_names if keyword.lower() in s.lower()), None)
        
    def safe_str(val):
        if pd.isna(val) or val is None:
            return None
        return str(val).strip()

    def safe_float(val):
        try:
            f = float(val)
            return 0.0 if (np.isnan(f) or np.isinf(f)) else f
        except Exception:
            return 0.0

    def safe_int(val):
        try:
            return int(float(val))
        except Exception:
            return 0
            
    def parse_date(df, col_pattern):
        col = next((c for c in df.columns if col_pattern.lower() in c.lower()), None)
        if col:
            return pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')
        return None

    # Sync frota
    print("Syncing frota...")
    cur.execute("DELETE FROM frota")
    s_frota = find_sheet('frota')
    if s_frota:
        df = pd.read_excel(xlsx_path, sheet_name=s_frota)
        for _, row in df.iterrows():
            id_val = safe_int(row.get('IDVeiculo'))
            if id_val <= 0:
                continue
            cur.execute("""
                INSERT INTO frota (id, placa, empresa, marca, modelo, status, tipagem, implemento, valor_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                id_val,
                safe_str(row.get('Placa')),
                None,  # No empresa column in excel
                safe_str(row.get('Marca')),
                safe_str(row.get('Modelo')),
                safe_str(row.get('Status')),
                safe_str(row.get('Tipagem')),
                safe_str(row.get('Implemento')),
                safe_float(row.get('ValorTotal'))
            ))

    # Sync fat_unitario
    print("Syncing fat_unitario...")
    cur.execute("DELETE FROM fat_unitario")
    s_fat_unitario = find_sheet('fat_unitario')
    if s_fat_unitario:
        df = pd.read_excel(xlsx_path, sheet_name=s_fat_unitario)
        df['_date'] = parse_date(df, 'mes')
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO fat_unitario (mes, id_veiculo, contrato, medicao, trabalhado, parado)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                row.get('_date'),
                safe_int(row.get('IDVeiculo')),
                safe_str(row.get('Contrato')),
                safe_float(row.get('Medicao')),
                safe_int(row.get('Trabalhado')),
                safe_int(row.get('Parado'))
            ))

    # Sync reembolsos
    print("Syncing reembolsos...")
    cur.execute("DELETE FROM reembolsos")
    s_reembolsos = find_sheet('reemb')
    if s_reembolsos:
        df = pd.read_excel(xlsx_path, sheet_name=s_reembolsos)
        df['_date'] = parse_date(df, 'emiss')
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO reembolsos (emissao, id_veiculo, valor_reembolso)
                VALUES (?, ?, ?)
            """, (
                row.get('_date'),
                safe_int(row.get('IDVeiculo')),
                safe_float(row.get('ValorReembolso'))
            ))

    # Sync faturamento
    print("Syncing faturamento...")
    cur.execute("DELETE FROM faturamento")
    s_faturamento = find_sheet('faturamento')
    if s_faturamento:
        df = pd.read_excel(xlsx_path, sheet_name=s_faturamento)
        df['_date'] = parse_date(df, 'emiss')
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO faturamento (id, emissao, valor_locacoes, valor_recebido)
                VALUES (?, ?, ?, ?)
            """, (
                safe_int(row.get('IDFatura')),
                row.get('_date'),
                safe_float(row.get('ValorLocacoes')),
                safe_float(row.get('ValorRecebido'))
            ))

    # Sync seguro_mensal
    print("Syncing seguro_mensal...")
    cur.execute("DELETE FROM seguro_mensal")
    s_seguros = find_sheet('seguro_mensal')
    if s_seguros:
        df = pd.read_excel(xlsx_path, sheet_name=s_seguros)
        df['_date'] = parse_date(df, 'vencimento')
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO seguro_mensal (vencimento, id_veiculo, valor)
                VALUES (?, ?, ?)
            """, (
                row.get('_date'),
                safe_int(row.get('IDVeiculo')),
                safe_float(row.get('Valor'))
            ))

    # Sync impostos
    print("Syncing impostos...")
    cur.execute("DELETE FROM impostos")
    s_impostos = find_sheet('impostos')
    if s_impostos:
        df = pd.read_excel(xlsx_path, sheet_name=s_impostos)
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO impostos (ano_imposto, id_veiculo, valor_total_final)
                VALUES (?, ?, ?)
            """, (
                safe_int(row.get('AnoImposto')),
                safe_int(row.get('IDVeiculo')),
                safe_float(row.get('ValorTotalFinal'))
            ))

    # Sync rastreamento
    print("Syncing rastreamento...")
    cur.execute("DELETE FROM rastreamento")
    s_rast = find_sheet('rastreamento')
    if s_rast:
        df = pd.read_excel(xlsx_path, sheet_name=s_rast)
        df['_date'] = parse_date(df, 'vencimento')
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO rastreamento (vencimento, id_veiculo, valor)
                VALUES (?, ?, ?)
            """, (
                row.get('_date'),
                safe_int(row.get('IDVeiculo')),
                safe_float(row.get('Valor'))
            ))

    conn.commit()
    conn.close()
    print("Sync complete.")

if __name__ == '__main__':
    sync()
