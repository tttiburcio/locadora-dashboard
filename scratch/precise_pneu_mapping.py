import pandas as pd

path = r'c:\Users\ADM\Documents\locadora-dashboard\Locadora.xlsx'
xl = pd.ExcelFile(path)
sheet = next(s for s in xl.sheet_names if 'MANUTENCOES' in s)
df = xl.parse(sheet)

# Grab only the 2 newest purchases
codes = ['OS-2025-0112', 'OS-2025-0088']
relevant = df[(df['Placa'] == 'CSU3F94') & (df['IDOrdServ'].isin(codes))]

print("CRITICAL AUDIT OF CSU3F94 RECENT PURCHASES:")
for idx, row in relevant.drop_duplicates(subset=['IDOrdServ', 'Descricao']).iterrows():
    print(f"\nOS: {row['IDOrdServ']} ({row['DataExecução']})")
    print(f"  Posição: {row.get('PosiçãoPneu')}")
    print(f"  Descrição: {row.get('Descricao')}")
    print(f"  Marca/Modelo: {row.get('MarcaPneu')} / {row.get('ModeloPneu')}")
    print(f"  Qtd: {row.get('QtdPneu')}")
