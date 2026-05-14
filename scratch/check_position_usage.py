import pandas as pd

path = r'c:\Users\ADM\Documents\locadora-dashboard\Locadora.xlsx'
xl = pd.ExcelFile(path)
sheet = next(s for s in xl.sheet_names if 'MANUTENCOES' in s)
df = xl.parse(sheet)

# Look for instances of "Traseiro" anywhere in the PosiçãoPneu column of the entire file
col = next((c for c in df.columns if 'Posi' in c and 'Pneu' in c), None)
if col:
    counts = df[col].value_counts()
    print("Value counts for position column in entire file:")
    print(counts)
else:
    print("Position column not found in file.")
