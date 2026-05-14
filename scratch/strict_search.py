import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///locadora.db")

def test_query_full(year):
    query = """
        SELECT os.numero_os as IDOrdServ, os.placa as Placa,
               COALESCE(os.data_execucao, os.data_entrada) as DataExecução
        FROM ordens_servico os
        WHERE os.deletado_em IS NULL
          AND (
            EXISTS (
              SELECT 1 FROM notas_fiscais nf
              JOIN manutencao_parcelas p ON p.nf_id = nf.id
              WHERE nf.os_id = os.id AND nf.deletado_em IS NULL AND p.deletado_em IS NULL
                AND strftime('%Y', p.data_vencimento) = :year
            )
            OR strftime('%Y', COALESCE(os.data_execucao, os.data_entrada)) = :year
          )
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params={"year": str(year)})
    return df

res = test_query_full(2026)
print("Found OS-2026-0214:", 'OS-2026-0214' in res['IDOrdServ'].values)
print("Rows around tail:")
print(res.tail())
