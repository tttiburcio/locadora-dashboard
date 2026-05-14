import sqlite3
conn = sqlite3.connect('locadora.db')
cur = conn.cursor()

for table in ['notas_fiscais', 'manutencao_parcelas']:
    cur.execute(f"PRAGMA table_info({table})")
    not_null = [c[1] for c in cur.fetchall() if c[3] == 1 and c[4] is None] # column 3 is 'notnull', column 4 is 'dflt_value'
    print(f"{table} NOT NULLS NO DEFAULT: {not_null}")

conn.close()
