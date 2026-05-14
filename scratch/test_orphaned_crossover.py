import pandas as pd
path = r'c:\Users\ADM\Documents\locadora-dashboard\Locadora.xlsx'
xl = pd.ExcelFile(path)
sheet = next(s for s in xl.sheet_names if 'MANUTENCOES' in s)
df = xl.parse(sheet)
df = df.dropna(subset=['Placa'])

df['DataExecução'] = pd.to_datetime(df['DataExecução'], errors='coerce')
df['Data Venc.'] = pd.to_datetime(df['Data Venc.'], errors='coerce')

# Find crossover rows executed < 2026 but due in 2026 AND WITHOUT IDOrdServ
cross_no_id = df[
    (df['DataExecução'].dt.year < 2026) &
    (df['Data Venc.'].dt.year == 2026) &
    (df['IDOrdServ'].isna())
]

print(f"Found {len(cross_no_id)} crossover installments MISSING IDOrdServ.")
if not cross_no_id.empty:
    print(cross_no_id[['Placa', 'DataExecução', 'Data Venc.', 'TotalOS', 'ValorParcela']])
