import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///locadora.db")

def test_query(year):
    query = """
        SELECT os.id as id_sql, os.id_veiculo as IDVeiculo, os.placa as Placa,
               os.numero_os as IDOrdServ
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

res = test_query(2026)
print("Testing if OS-2026-0201 is in query output...")
match = res[res['IDOrdServ'] == 'OS-2026-0201']
if not match.empty:
    print("FOUND OS-2026-0201!! Details:")
    print(match)
else:
    print("NOT FOUND OS-2026-0201. Running simpler queries to find breakdown...")
    with engine.connect() as c:
        c1 = c.execute(text("SELECT 1 FROM ordens_servico WHERE numero_os = 'OS-2026-0201' AND deletado_em IS NULL")).fetchone()
        print("Condition A (os exists, not deleted):", c1)
        c2 = c.execute(text("""
            SELECT COUNT(*) FROM notas_fiscais nf
            JOIN manutencao_parcelas p ON p.nf_id = nf.id
            JOIN ordens_servico os ON nf.os_id = os.id
            WHERE os.numero_os = 'OS-2026-0201' AND nf.deletado_em IS NULL AND p.deletado_em IS NULL
            AND strftime('%Y', p.data_vencimento) = '2026'
        """)).fetchone()
        print("Condition B (exists count matches):", c2)
