import pandas as pd

path = r'c:\Users\ADM\Documents\locadora-dashboard\Locadora.xlsx'
xl = pd.ExcelFile(path)
sheet = next(s for s in xl.sheet_names if 'MANUTENCOES' in s)
df = xl.parse(sheet)
df = df.dropna(subset=['Placa'])

relevant = df[(df['Placa'] == 'CSU3F94') & (df['Sistema'].str.lower() == 'pneu')]
print("Excel Rows for Pneu (CSU3F94):")
cols = ['IDOrdServ', 'DataExecução', 'Serviço', 'PosiçãoPneu', 'MarcaPneu', 'ModeloPneu', 'EspecifPneu', 'CondiçãoPneu', 'ManejoPneu']
available = [c for c in cols if c in relevant.columns]
print(relevant[available].sort_values('DataExecução', ascending=False))
