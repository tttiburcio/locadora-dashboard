import pandas as pd
path = r'c:\Users\ADM\Documents\locadora-dashboard\Locadora.xlsx'
xl = pd.ExcelFile(path)
sheet = next(s for s in xl.sheet_names if 'MANUTENCOES' in s)
df = xl.parse(sheet)
df = df.dropna(subset=['Placa'])

# Check rows where DataExecução is missing but we have other signals of cost
missing_exec = df[df['DataExecução'].isna()]
print(f"Found {len(missing_exec)} rows with Placa but missing DataExecução.")
if len(missing_exec) > 0:
    print("\nSamples of rows missing DataExecução:")
    print(missing_exec[['Placa', 'TotalOS', 'Data Venc.', 'IDOrdServ', 'Fornecedor']].tail(5))
else:
    print("No rows found missing DataExecução.")
