import pandas as pd
path = r'c:\Users\ADM\Documents\locadora-dashboard\Locadora.xlsx'
xl = pd.ExcelFile(path)
sheet = next(s for s in xl.sheet_names if 'MANUTENCOES' in s)
df = xl.parse(sheet)
df = df.dropna(subset=['Placa'])

df['DataExecução'] = pd.to_datetime(df['DataExecução'], errors='coerce')
df['Data Venc.'] = pd.to_datetime(df['Data Venc.'], errors='coerce')

# Find Excel rows lost by line 1075 filtering
lost_rows = df[
    (df['DataExecução'].isna()) & 
    (df['Data Venc.'].dt.year == 2026)
]

print(f"Confirmed: {len(lost_rows)} rows lost due to missing execution date, despite 2026 payment dates.")
if not lost_rows.empty:
    print("\nSamples of lost values:")
    print(lost_rows[['Placa', 'IDOrdServ', 'Data Venc.', 'TotalOS']].head(10))
    print("\nTotal sum of lost value across these rows (assuming non-deduped):", lost_rows['TotalOS'].sum())
