import sqlite3
import pandas as pd
import os

db_path = 'locadora.db'
xlsx_path = 'Locadora.xlsx'

def sync_faturamento():
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    xl = pd.ExcelFile(xlsx_path)
    sheet = next((s for s in xl.sheet_names if 'faturamento' in s.lower()), None)
    if not sheet:
        print("Sheet faturamento not found.")
        return
    
    df = pd.read_excel(xlsx_path, sheet_name=sheet)
    
    # Mapping
    # IDFatura -> id
    # Emissão -> emissao (convert to string YYYY-MM-DD)
    # ValorLocacoes -> valor_locacoes
    # ValorRecebido -> valor_recebido
    
    # Pre-process
    df['Emissão'] = pd.to_datetime(df['Emissão']).dt.strftime('%Y-%m-%d')
    
    updated = 0
    inserted = 0
    
    for _, row in df.iterrows():
        id_val = int(row['IDFatura'])
        emissao = row['Emissão']
        v_loc = float(row['ValorLocacoes']) if pd.notnull(row['ValorLocacoes']) else 0.0
        v_rec = float(row['ValorRecebido']) if pd.notnull(row['ValorRecebido']) else 0.0
        
        # Check if exists
        cur.execute("SELECT id FROM faturamento WHERE id = ?", (id_val,))
        exists = cur.fetchone()
        
        if exists:
            cur.execute("""
                UPDATE faturamento 
                SET emissao = ?, valor_locacoes = ?, valor_recebido = ?
                WHERE id = ?
            """, (emissao, v_loc, v_rec, id_val))
            updated += 1
        else:
            cur.execute("""
                INSERT INTO faturamento (id, emissao, valor_locacoes, valor_recebido)
                VALUES (?, ?, ?, ?)
            """, (id_val, emissao, v_loc, v_rec))
            inserted += 1
            
    conn.commit()
    conn.close()
    print(f"Sync complete. Updated: {updated}, Inserted: {inserted}")

if __name__ == "__main__":
    sync_faturamento()
