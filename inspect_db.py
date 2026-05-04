import sqlite3

db = 'locadora.db'
try:
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"Tables in {db}:", tables)
    for t in tables:
        cursor.execute(f"PRAGMA table_info({t[0]})")
        print(f"  Schema for {t[0]}:", cursor.fetchall())
except Exception as e:
    print(f"Error {db}:", e)
