import pandas as pd
path = r'c:\Users\ADM\Documents\locadora-dashboard\Locadora.xlsx'
xl = pd.ExcelFile(path)
sheet = next(s for s in xl.sheet_names if 'MANUTENCOES' in s)
df = xl.parse(sheet)
df = df.dropna(subset=['Placa'])

df['DataExecução'] = pd.to_datetime(df['DataExecução'], errors='coerce')
df['Data Venc.'] = pd.to_datetime(df['Data Venc.'], errors='coerce')

# Find rows executed in 2025 (or older) but due in 2026
cross_year = df[
    (df['DataExecução'].dt.year < 2026) &
    (df['Data Venc.'].dt.year == 2026)
]

print(f"Found {len(cross_year)} installments executed before 2026 but falling due in 2026.")
if not cross_year.empty:
    print("\nExamples of across-year entries missed by current logic:")
    print(cross_year[['Placa', 'IDOrdServ', 'DataExecução', 'Data Venc.', 'TotalOS', 'ValorParcela']].head(10))
else:
    print("No crossover entries found in Excel.")
