from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

try:
    # Delete existing counters to avoid conflict
    db.execute(text('DELETE FROM os_counters'))

    # Get the highest OS number for each year
    result = db.execute(text("""
        SELECT 
            CAST(SUBSTR(numero_os, 4, 4) AS INTEGER) AS ano,
            MAX(CAST(SUBSTR(numero_os, 9) AS INTEGER)) AS ultimo
        FROM ordens_servico 
        WHERE numero_os IS NOT NULL
        GROUP BY ano
    """)).fetchall()

    for row in result:
        ano, ultimo = row[0], row[1]
        if ano and ultimo:
            db.execute(text('INSERT INTO os_counters (ano, ultimo) VALUES (:a, :u)'), {'a': ano, 'u': ultimo})
            print(f'Ano {ano}: Ultimo {ultimo}')

    # Find OS-2026-0001 and rename to next available
    os1 = db.execute(text('SELECT id FROM ordens_servico WHERE numero_os = "OS-2026-0001"')).fetchone()
    if os1:
        os_id = os1[0]
        next_num = 203
        db.execute(text('UPDATE ordens_servico SET numero_os = "OS-2026-0203" WHERE id = :id'), {'id': os_id})
        # Update counter
        db.execute(text('UPDATE os_counters SET ultimo = 203 WHERE ano = 2026'))
        print('Renamed OS-2026-0001 to OS-2026-0203 and updated counter')

    db.commit()
    print("Fix applied successfully.")

except Exception as e:
    db.rollback()
    print(f"Error: {e}")
finally:
    db.close()
