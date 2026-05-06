import sqlite3
from pathlib import Path

db_path = Path('locadora.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Parcela 2 da NF 923535
# Atualmente existem duas parcelas marcadas como 1/2 (IDs 532 e 533).
# Vou transformar o ID 533 na parcela 2/2 e alterar o vencimento para 05/06/2026.

target_id = 533
new_date = '2026-06-05'
new_num = 2

print(f"Atualizando parcela ID {target_id}...")
cursor.execute("""
    UPDATE manutencao_parcelas 
    SET parcela_atual = ?, data_vencimento = ? 
    WHERE id = ?
""", (new_num, new_date, target_id))

conn.commit()
print("Sucesso: Parcela 2 atualizada para 05/06/2026.")

conn.close()
