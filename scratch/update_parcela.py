import sqlite3
from pathlib import Path

db_path = Path('locadora.db')
if not db_path.exists():
    print(f"Erro: Banco de dados não encontrado em {db_path.absolute()}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Busca a parcela específica
# NF: 923535, Parcela: 2
# Novo vencimento: 05/06/2026 (formato ISO YYYY-MM-DD para SQLite)
new_date = '2026-06-05'

print("Buscando parcelas da NF 923535...")
cursor.execute("SELECT id, nota, parcela_atual, parcela_total, data_vencimento FROM manutencao_parcelas WHERE nota = '923535' AND deletado_em IS NULL")
rows = cursor.fetchall()

if not rows:
    print("Nenhuma parcela encontrada para a NF 923535.")
    conn.close()
    exit(0)

target_id = None
for row in rows:
    pid, nota, atual, total, venc = row
    print(f"ID: {pid} | NF: {nota} | Parcela: {atual}/{total} | Vencimento: {venc}")
    if int(atual) == 2:
        target_id = pid

if target_id:
    print(f"Atualizando ID {target_id} para {new_date}...")
    cursor.execute("UPDATE manutencao_parcelas SET data_vencimento = ? WHERE id = ?", (new_date, target_id))
    conn.commit()
    print("Atualização concluída com sucesso.")
else:
    print("Parcela 2 não encontrada para esta NF.")

conn.close()
