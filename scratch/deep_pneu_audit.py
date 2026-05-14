import pandas as pd

path = r'c:\Users\ADM\Documents\locadora-dashboard\Locadora.xlsx'
xl = pd.ExcelFile(path)
sheet = next(s for s in xl.sheet_names if 'MANUTENCOES' in s)
df = xl.parse(sheet)

relevant = df[(df['Placa'] == 'CSU3F94') & (df['Sistema'].str.lower().fillna('') == 'pneu')]
relevant = relevant.dropna(how='all', axis=1)

print("ALL NON-NULL COLUMNS FOR PNEU EVENTS (CSU3F94):")
for idx, row in relevant.sort_values('DataExecução', ascending=False).iterrows():
    print(f"\n-- OS: {row.get('IDOrdServ')} on {row.get('DataExecução')} --")
    for col, val in row.items():
        if pd.notna(val):
            print(f"  {col}: {val}")
