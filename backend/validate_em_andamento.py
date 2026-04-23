import sys
sys.path.insert(0, '.')
import pandas as pd
from database import SessionLocal
import models

xl = pd.ExcelFile('../Locadora.xlsx')
manut = xl.parse('\U0001f527 MANUTENCOES')

date_col = next((c for c in manut.columns if 'DataExecu' in c or 'Data Execu' in c), None)

# === Em andamento no Excel: sem data de execucao e com placa preenchida ===
sem_data = manut[manut[date_col].isna() & manut['Placa'].notna()].copy()
has_os   = sem_data[sem_data['IDOrdServ'].notna()].drop_duplicates(subset=['IDOrdServ'])
no_os    = sem_data[sem_data['IDOrdServ'].isna()]
excel_em_andamento = pd.concat([has_os, no_os], ignore_index=True)

print(f'{"="*60}')
print(f'OS EM ANDAMENTO NO EXCEL: {len(excel_em_andamento)}')
print(f'{"="*60}')
for _, r in excel_em_andamento.iterrows():
    id_ord = r.get('IDOrdServ', None)
    id_str = str(id_ord).strip() if pd.notna(id_ord) else 'sem IDOrdServ'
    print(f'  Placa={r["Placa"]:12s} | IDOrdServ={id_str}')

# === Estado atual do banco ===
db = SessionLocal()
os_db = db.query(models.OrdemServico).filter(
    models.OrdemServico.deletado_em.is_(None)
).all()

db_por_status = {}
for o in os_db:
    db_por_status.setdefault(o.status_os, []).append(o)

print(f'\n{"="*60}')
print('STATUS NO BANCO (ordens_servico):')
print(f'{"="*60}')
for status, lista in sorted(db_por_status.items()):
    print(f'  {status}: {len(lista)}')

# === Validacao cruzada ===
print(f'\n{"="*60}')
print('VALIDACAO CRUZADA — Excel EM ANDAMENTO vs Banco:')
print(f'{"="*60}')

em_andamento_no_banco = [o for o in os_db if o.status_os == 'em_andamento']
placas_banco = {o.placa for o in em_andamento_no_banco}

nao_encontradas = []
for _, r in excel_em_andamento.iterrows():
    placa = str(r['Placa']).strip()
    id_ord = str(r.get('IDOrdServ', '')).strip() if pd.notna(r.get('IDOrdServ', float('nan'))) else None

    encontrou = any(
        o.placa == placa and o.status_os == 'em_andamento'
        for o in os_db
    )
    if not encontrou:
        nao_encontradas.append({'placa': placa, 'id_ord': id_ord})

if nao_encontradas:
    print(f'\n  FALTANDO no banco ({len(nao_encontradas)}):')
    for item in nao_encontradas:
        print(f'    Placa={item["placa"]} | IDOrdServ={item["id_ord"]}')
else:
    print('\n  Todas as OS em andamento do Excel estao no banco. OK!')

print(f'\n{"="*60}')
print('OS EM ANDAMENTO NO BANCO:')
print(f'{"="*60}')
for o in sorted(em_andamento_no_banco, key=lambda x: x.placa or ''):
    item = o.itens[0] if o.itens else None
    print(f'  id={o.id:4d} | placa={o.placa:12s} | numero_os={o.numero_os or "—":20s} | sistema={item.sistema if item else "—"}')

db.close()
