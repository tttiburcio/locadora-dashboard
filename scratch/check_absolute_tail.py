import pandas as pd
path = r'c:\Users\ADM\Documents\locadora-dashboard\Locadora.xlsx'
xl = pd.ExcelFile(path)
sheet = next(s for s in xl.sheet_names if 'MANUTENCOES' in s)
df = xl.parse(sheet)
df_clean = df.dropna(subset=['Placa', 'Fornecedor'], how='all')
print("Tail of cleaned Excel maintenance sheet:")
print(df_clean[['Placa', 'IDOrdServ', 'DataExecução', 'Data Venc.', 'TotalOS', 'Fornecedor']].tail(15))
