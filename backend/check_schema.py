import sqlite3
conn = sqlite3.connect(r'C:\Users\vinic\Documents\clone\locadora.db')
schema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='nf_itens'").fetchone()
print(schema[0] if schema else 'Not found')
conn.close()
