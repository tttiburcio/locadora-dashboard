import pandas as pd
from pathlib import Path

EXCEL_PATH = Path('Locadora.xlsx')
with pd.ExcelFile(EXCEL_PATH) as xl:
    df = xl.parse('🔧 MANUTENCOES')
    date_col = next((c for c in df.columns if "DataExecu" in c or "Data Execu" in c), None)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        years = df[date_col].dt.year.dropna().unique()
        print(f"Years in Manutencoes: {sorted(years)}")
    else:
        print("Date column not found")
