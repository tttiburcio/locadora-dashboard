"""
FASE FINAL — FA2: Enriquecer tabela reembolsos (já existe de fase anterior).
A tabela tem 51 linhas com id=IDReembolso — apenas adiciona colunas extras.
Idempotente: UPDATE ... WHERE campo IS NULL.
"""
import sqlite3, os, sys, io
import pandas as pd
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")
XL_PATH = os.path.join(ROOT, "Locadora.xlsx")
ABA     = "↩️ REEMBOLSOS"


def safe_date(val):
    if pd.isna(val) or val is None:
        return None
    try:
        return str(pd.to_datetime(val))[:10]
    except Exception:
        return None


def safe_float(val):
    if pd.isna(val) or val is None:
        return 0.0
    try:
        return float(val)
    except Exception:
        return 0.0


def main():
    print("=" * 70)
    print("FASE FINAL — FA2: Enriquecer Reembolsos")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    df = pd.read_excel(XL_PATH, sheet_name=ABA)
    print(f"Excel: {len(df)} linhas lidas de '{ABA}'")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM reembolsos")
    total_antes = cur.fetchone()[0]
    print(f"SQL antes: {total_antes} linhas")

    # Mapa id_veiculo → placa
    cur.execute("SELECT id, placa FROM frota")
    id_to_placa = {row[0]: row[1] for row in cur.fetchall()}
    cur.execute("SELECT id FROM frota")
    ids_frota = {row[0] for row in cur.fetchall()}

    atualizados = 0
    erros = 0

    try:
        con.execute("BEGIN")
        for _, row in df.iterrows():
            id_excel = int(row["IDReembolso"]) if pd.notna(row.get("IDReembolso")) else None
            if id_excel is None:
                continue

            id_veiculo_xl = row.get("IDVeiculo")
            id_veiculo = int(id_veiculo_xl) if pd.notna(id_veiculo_xl) and int(id_veiculo_xl) in ids_frota else None
            placa = id_to_placa.get(id_veiculo) if id_veiculo else None

            try:
                cur.execute("""
                    UPDATE reembolsos SET
                        placa              = COALESCE(placa, ?),
                        vencimento         = COALESCE(vencimento, ?),
                        empresa            = COALESCE(empresa, ?),
                        valor_recebido     = COALESCE(valor_recebido, ?),
                        status_recebimento = COALESCE(status_recebimento, ?),
                        tipo               = COALESCE(tipo, ?),
                        id_contrato_excel  = COALESCE(id_contrato_excel, ?),
                        id_cliente_excel   = COALESCE(id_cliente_excel, ?),
                        origem             = COALESCE(origem, 'excel_legado')
                    WHERE id = ?
                """, (
                    placa,
                    safe_date(row.get("Vencimento")),
                    str(row["Empresa"]) if pd.notna(row.get("Empresa")) else None,
                    safe_float(row.get("ValorRecebido")),
                    str(row["StatusRecebimento"]) if pd.notna(row.get("StatusRecebimento")) else None,
                    str(row["Tipo"]) if pd.notna(row.get("Tipo")) else None,
                    int(row["IDContrato"]) if pd.notna(row.get("IDContrato")) else None,
                    int(row["IDCliente"]) if pd.notna(row.get("IDCliente")) else None,
                    id_excel,
                ))
                if cur.rowcount:
                    atualizados += 1
            except Exception as e:
                erros += 1
                print(f"  ERRO id={id_excel}: {e}")

        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise RuntimeError(f"Erro na atualização de reembolsos: {e}")

    cur.execute("SELECT COUNT(*) FROM reembolsos")
    total_depois = cur.fetchone()[0]
    cur.execute("SELECT SUM(valor_reembolso) FROM reembolsos")
    soma_sql = cur.fetchone()[0] or 0

    valor_excel = df["ValorReembolso"].sum()
    print(f"\nResultados:")
    print(f"  Atualizados:  {atualizados}")
    print(f"  Erros:        {erros}")
    print(f"  Total SQL:    {total_depois}  (antes: {total_antes})")

    diff_pct = abs(soma_sql - valor_excel) / max(abs(valor_excel), 1) * 100
    ok = "✓" if diff_pct < 1 else f"⚠ divergência {diff_pct:.2f}%"
    print(f"\nVerificação:")
    print(f"  Soma Excel: R$ {valor_excel:,.2f}")
    print(f"  Soma SQL:   R$ {soma_sql:,.2f}")
    print(f"  Diferença:  {diff_pct:.4f}%  {ok}")

    # Cobertura das novas colunas
    cur.execute("SELECT COUNT(*) FROM reembolsos WHERE placa IS NOT NULL")
    print(f"  placa preenchida: {cur.fetchone()[0]}/{total_depois}")
    cur.execute("SELECT COUNT(*) FROM reembolsos WHERE origem IS NOT NULL")
    print(f"  origem preenchida: {cur.fetchone()[0]}/{total_depois}")

    con.close()
    print(f"\nFA2 concluído: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
