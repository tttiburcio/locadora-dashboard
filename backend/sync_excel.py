import os
import sys

# 1. Wipes the DB and recreates it from Locadora.xlsx (legacy tables)
print("--- Passo 1: Importando Excel (migrate_excel.py) ---")
ret = os.system("python migrate_excel.py")
if ret != 0:
    print("Erro no migrate_excel.py")
    sys.exit(1)

# 2. Convert legacy Manutencao -> OrdemServico (new model)
print("\n--- Passo 2: Convertendo para o novo modelo (1:1) ---")
sys.path.insert(0, '.')
import main
main._migrate_1to1_safe()

# 3. Fix "em_andamento" status for OS without execution date
print("\n--- Passo 3: Corrigindo status 'em_andamento' ---")
os.system("python fix_em_andamento.py")

print("\n=== SINCRONIZACAO CONCLUIDA COM SUCESSO ===")
