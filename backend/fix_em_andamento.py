import sys
sys.path.insert(0, '.')
import pandas as pd
from database import SessionLocal
import models

xl = pd.ExcelFile('../Locadora.xlsx')
manut = xl.parse('\U0001f527 MANUTENCOES')

# Identifica coluna de data com encoding variavel
date_col = next((c for c in manut.columns if 'DataExecu' in c or 'Data Execu' in c), None)
serv_col = next((c for c in manut.columns if 'Servi' in c), 'Servico')
print(f'Coluna data: {date_col}')

# Registros SEM data de execucao E com placa preenchida = em andamento reais
sem_data = manut[manut[date_col].isna() & manut['Placa'].notna()].copy()

# Dedup por IDOrdServ
has_os = sem_data[sem_data['IDOrdServ'].notna()].drop_duplicates(subset=['IDOrdServ'])
no_os  = sem_data[sem_data['IDOrdServ'].isna()]
em_andamento = pd.concat([has_os, no_os], ignore_index=True)

print(f'OS em andamento no Excel: {len(em_andamento)}')
for _, r in em_andamento.iterrows():
    id_ord = r.get('IDOrdServ', None)
    id_str = str(id_ord).strip() if pd.notna(id_ord) else 'sem OS'
    print(f'  Placa={r["Placa"]} | IDOrdServ={id_str}')

# Corrige status no banco
db = SessionLocal()
updated = 0

for _, row in em_andamento.iterrows():
    placa = str(row['Placa']).strip()
    id_ord = row.get('IDOrdServ', None)

    # Tenta encontrar pela OS number first
    os_obj = None
    if pd.notna(id_ord):
        id_ord_str = str(id_ord).strip()
        os_obj = db.query(models.OrdemServico).filter(
            models.OrdemServico.numero_os.like(f'%{id_ord_str}%'),
            models.OrdemServico.deletado_em.is_(None)
        ).first()

    # Fallback: busca por placa sem data_execucao
    if not os_obj:
        os_obj = db.query(models.OrdemServico).filter(
            models.OrdemServico.placa == placa,
            models.OrdemServico.data_execucao.is_(None),
            models.OrdemServico.deletado_em.is_(None)
        ).first()

    if os_obj and os_obj.status_os == 'finalizada':
        os_obj.status_os = 'em_andamento'
        updated += 1
        print(f'  -> Corrigido: OS id={os_obj.id} placa={os_obj.placa} status=em_andamento')

db.commit()
db.close()
print(f'\nTotal de OS atualizadas para em_andamento: {updated}')
