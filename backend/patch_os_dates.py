import sys
sys.path.insert(0, '.')
from database import SessionLocal
import models
from datetime import datetime

dates = {
    '0146': '06/08/2025',
    '0191': '17/03/2026',
    '0193': '13/04/2026',
    '0194': '10/04/2026',
    '0195': '31/03/2026',
    '0196': '08/04/2026',
    '0198': '04/03/2026',
    '0201': '15/04/2026'
}

db = SessionLocal()
count = 0
for os_suf, date_str in dates.items():
    dt = datetime.strptime(date_str, '%d/%m/%Y').date()
    # Find the OS
    os_objs = db.query(models.OrdemServico).filter(models.OrdemServico.numero_os.like(f'%{os_suf}')).all()
    for obj in os_objs:
        obj.data_execucao = dt
        obj.status_os = 'finalizada'
        count += 1
        print(f"Atualizado {obj.numero_os} para finalizada com data {dt}")

db.commit()
db.close()
print(f"Total atualizadas para finalizadas: {count}")
