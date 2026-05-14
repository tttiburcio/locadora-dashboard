import sys
import os
sys.path.append(r'c:\Users\ADM\Documents\locadora-dashboard\backend')

import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, selectinload
import models
import schemas

DATABASE_URL = "sqlite:///c:/Users/ADM/Documents/locadora-dashboard/locadora.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    print("Attempting manual fetch and model serialization...")
    q = (
        db.query(models.OrdemServico)
        .options(
            selectinload(models.OrdemServico.itens),
            selectinload(models.OrdemServico.notas_fiscais)
            .selectinload(models.NotaFiscal.parcelas),
        )
        .filter(models.OrdemServico.deletado_em.is_(None))
    )
    results = q.all()
    print(f"Fetched {len(results)} rows from DB.")
    
    print("Starting row-by-row pydantic validation to catch the offender...")
    for idx, obj in enumerate(results):
        try:
            schemas.OsResponse.model_validate(obj)
        except Exception as e:
            print(f"\nCRASH AT ROW {idx} (ID={obj.id}, OS={obj.numero_os})")
            print("ERROR TYPE:", type(e).__name__)
            print("ERROR MSG:", e)
            sys.exit(1)
    print("All rows passed validation! No serialization error detected in OsResponse??")
except Exception as e:
    print("UNHANDLED CRASH:", e)
finally:
    db.close()
