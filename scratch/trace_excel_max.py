import pandas as pd

path = r'c:\Users\ADM\Documents\locadora-dashboard\Locadora.xlsx'
xl = pd.ExcelFile(path)
sheet = next(s for s in xl.sheet_names if 'MANUTENCOES' in s)
df = xl.parse(sheet)
df = df.dropna(subset=['Placa'])

relevant = df[df['Placa'] == 'MAX4116']
print("Excel Rows for MAX4116:")
print(relevant[['IDOrdServ', 'DataExecução', 'Data Venc.', 'TotalOS']])
