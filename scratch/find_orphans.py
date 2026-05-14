import pandas as pd
path = r'c:\Users\ADM\Documents\locadora-dashboard\Locadora.xlsx'
xl = pd.ExcelFile(path)
sheet = next(s for s in xl.sheet_names if 'MANUTENCOES' in s)
df = xl.parse(sheet)
df = df.dropna(subset=['Placa'])

# Check rows missing BOTH DataExecução AND IDOrdServ
orphans = df[df['DataExecução'].isna() & df['IDOrdServ'].isna()]
print(f"Found {len(orphans)} manual entries missing BOTH DataExecução and IDOrdServ.")
if len(orphans) > 0:
    print("\nPreview of orphaned entries:")
    print(orphans[['Placa', 'TotalOS', 'Data Venc.', 'Fornecedor']].tail(10))
else:
    print("No orphaned entries found.")
