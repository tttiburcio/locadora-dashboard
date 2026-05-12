"""
FASE FINAL — FA3: Migrar aba 🧾 FATURAMENTO do Excel → SQL tabela faturamento_mensal.
Idempotente via id_fatura_excel UNIQUE.
"""
import sqlite3, os, sys, io
import pandas as pd
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")
XL_PATH = os.path.join(ROOT, "Locadora.xlsx")
ABA     = "🧾 FATURAMENTO"


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
    print("FASE FINAL — FA3: Migrar Faturamento Mensal")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    df = pd.read_excel(XL_PATH, sheet_name=ABA)
    print(f"Excel: {len(df)} linhas lidas de '{ABA}'")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    inseridos = 0
    ignorados = 0
    erros = 0

    try:
        con.execute("BEGIN")
        for _, row in df.iterrows():
            id_excel = int(row["IDFatura"]) if pd.notna(row.get("IDFatura")) else None
            if id_excel is None:
                ignorados += 1
                continue

            emissao = safe_date(row.get("Emissão"))
            if not emissao:
                ignorados += 1
                continue

            # IDContrato pode ser "10;13" (múltiplos) — guardar como texto
            id_contrato = str(row["IDContrato"]) if pd.notna(row.get("IDContrato")) else None
            id_cliente  = int(row["IDCliente"]) if pd.notna(row.get("IDCliente")) else None

            try:
                cur.execute("""
                    INSERT OR IGNORE INTO faturamento_mensal
                        (id_fatura_excel, emissao, vencimento, valor_locacoes,
                         valor_recebido, status_recebimento, empresa,
                         id_contrato_excel, id_cliente_excel, origem)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'excel_legado')
                """, (
                    id_excel,
                    emissao,
                    safe_date(row.get("Vencimento")),
                    safe_float(row.get("ValorLocacoes")),
                    safe_float(row.get("ValorRecebido")),
                    str(row["StatusRecebimento"]) if pd.notna(row.get("StatusRecebimento")) else None,
                    str(row["Empresa"]) if pd.notna(row.get("Empresa")) else None,
                    id_contrato,
                    id_cliente,
                ))
                if cur.rowcount:
                    inseridos += 1
                else:
                    ignorados += 1
            except Exception as e:
                erros += 1
                print(f"  ERRO id_excel={id_excel}: {e}")

        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise RuntimeError(f"Erro na migração de faturamento: {e}")

    cur.execute("SELECT COUNT(*) FROM faturamento_mensal")
    total_sql = cur.fetchone()[0]
    cur.execute("SELECT SUM(valor_locacoes), SUM(valor_recebido) FROM faturamento_mensal")
    row_sql = cur.fetchone()
    soma_loc_sql = row_sql[0] or 0
    soma_rec_sql = row_sql[1] or 0

    soma_loc_xl = df["ValorLocacoes"].sum()
    soma_rec_xl = df["ValorRecebido"].sum()

    print(f"\nResultados:")
    print(f"  Inseridos:    {inseridos}")
    print(f"  Ignorados:    {ignorados}  (já existiam ou sem data)")
    print(f"  Erros:        {erros}")
    print(f"  Total SQL:    {total_sql}")

    print(f"\nVerificação de valores:")
    for lbl, xl_v, sql_v in [
        ("ValorLocacoes", soma_loc_xl, soma_loc_sql),
        ("ValorRecebido",  soma_rec_xl, soma_rec_sql),
    ]:
        diff = abs(sql_v - xl_v) / max(abs(xl_v), 1) * 100
        ok = "✓" if diff < 1 else f"⚠ divergência {diff:.2f}%"
        print(f"  {lbl:<18s} Excel={xl_v:,.2f}  SQL={sql_v:,.2f}  {ok}")

    con.close()
    print(f"\nFA3 concluído: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
