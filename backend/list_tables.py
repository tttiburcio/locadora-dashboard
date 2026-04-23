import sqlite3
conn = sqlite3.connect(r'C:\Users\vinic\Documents\clone\locadora.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print([t[0] for t in tables])
conn.close()
