"""
FASE FINAL — FA4: Migrar Empresas, Clientes, Contratos, Contrato_Veiculo do Excel → SQL.
Idempotente via INSERT OR IGNORE nas PKs.
"""
import sqlite3, os, sys, io
import pandas as pd
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")
XL_PATH = os.path.join(ROOT, "Locadora.xlsx")


def safe_date(val):
    if pd.isna(val) or val is None:
        return None
    try:
        return str(pd.to_datetime(val))[:10]
    except Exception:
        return None


def safe_str(val):
    if pd.isna(val) or val is None:
        return None
    s = str(val).strip()
    return s if s and s.lower() not in ("nan", "none", "nat") else None


def main():
    print("=" * 70)
    print("FASE FINAL — FA4: Migrar Empresas, Clientes, Contratos, Contrato_Veiculo")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    xl = pd.ExcelFile(XL_PATH)

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = OFF")
    cur = con.cursor()

    # ── 1. Empresas ───────────────────────────────────────────────────────────
    print("\n[1] Migrando Empresas...")
    df_emp = pd.read_excel(xl, sheet_name="🏢 EMPRESAS")
    ins_emp = 0
    for _, row in df_emp.iterrows():
        id_emp = int(row["IDEmpresa"]) if pd.notna(row.get("IDEmpresa")) else None
        if id_emp is None:
            continue
        cur.execute("""
            INSERT OR IGNORE INTO empresas (id, nome, cnpj_cpf, municipio, estado)
            VALUES (?, ?, ?, ?, ?)
        """, (
            id_emp,
            safe_str(row.get("RazaoSocial")),
            safe_str(row.get("CNPJ_CPF")),
            safe_str(row.get("Municipio")),
            safe_str(row.get("Estado")),
        ))
        if cur.rowcount:
            ins_emp += 1

    cur.execute("SELECT COUNT(*) FROM empresas")
    print(f"  Inseridos: {ins_emp}  |  Total SQL: {cur.fetchone()[0]}")

    # ── 2. Clientes ───────────────────────────────────────────────────────────
    print("\n[2] Migrando Clientes...")
    df_cli = pd.read_excel(xl, sheet_name="🏢 CLIENTES")
    ins_cli = 0
    for _, row in df_cli.iterrows():
        id_cli = int(row["IDCliente"]) if pd.notna(row.get("IDCliente")) else None
        if id_cli is None:
            continue
        cur.execute("""
            INSERT OR IGNORE INTO clientes (id, nome, cnpj_cpf, municipio, estado, status_cliente)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            id_cli,
            safe_str(row.get("RazaoSocial")),
            safe_str(row.get("CNPJ_CPF")),
            safe_str(row.get("MunicipioCliente")),
            safe_str(row.get("EstadoCliente")),
            safe_str(row.get("StatusCliente")),
        ))
        if cur.rowcount:
            ins_cli += 1

    cur.execute("SELECT COUNT(*) FROM clientes")
    print(f"  Inseridos: {ins_cli}  |  Total SQL: {cur.fetchone()[0]}")

    # ── 3. Contratos ──────────────────────────────────────────────────────────
    print("\n[3] Migrando Contratos...")
    df_con = pd.read_excel(xl, sheet_name="📄 CONTRATOS")
    ins_con = 0
    for _, row in df_con.iterrows():
        id_con = int(row["IDContrato"]) if pd.notna(row.get("IDContrato")) else None
        if id_con is None:
            continue
        emp_id = int(row["IDEmpresa"]) if pd.notna(row.get("IDEmpresa")) else None
        cli_id = int(row["IDCliente"]) if pd.notna(row.get("IDCliente")) else None
        cur.execute("""
            INSERT OR IGNORE INTO contratos
                (id, empresa_id, cliente_id, nome_cliente, cidade_operacao, estado_operacao,
                 data_inicio, data_fim, data_encerramento, status_contrato)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            id_con,
            emp_id,
            cli_id,
            safe_str(row.get("NomeCliente")),
            safe_str(row.get("CidadeOperacao")),
            safe_str(row.get("EstadoOperacao")),
            safe_date(row.get("DataInicio")),
            safe_date(row.get("DataFimPrevista")),
            safe_date(row.get("DataEncerramento")),
            safe_str(row.get("StatusContrato")),
        ))
        if cur.rowcount:
            ins_con += 1

    cur.execute("SELECT COUNT(*) FROM contratos")
    print(f"  Inseridos: {ins_con}  |  Total SQL: {cur.fetchone()[0]}")

    # ── 4. Contrato_Veiculo ───────────────────────────────────────────────────
    print("\n[4] Migrando Contrato_Veiculo...")
    df_cv = pd.read_excel(xl, sheet_name="🔗 CONTRATO_VEICULO")
    # Mapa IDVeiculo Excel → id SQL (são os mesmos neste projeto)
    cur.execute("SELECT id FROM frota")
    ids_frota = {row[0] for row in cur.fetchall()}

    ins_cv = 0
    for _, row in df_cv.iterrows():
        id_cv  = int(row["IDContratoVeiculo"]) if pd.notna(row.get("IDContratoVeiculo")) else None
        id_con = int(row["IDContrato"])        if pd.notna(row.get("IDContrato")) else None
        id_v   = int(row["IDVeiculo"])         if pd.notna(row.get("IDVeiculo")) else None
        if id_cv is None or id_con is None:
            continue

        # id_veiculo pode não existir na frota SQL
        id_veiculo_sql = id_v if id_v in ids_frota else None

        cur.execute("""
            INSERT OR IGNORE INTO contrato_veiculo (id, contrato_id, id_veiculo, sequencia)
            VALUES (?, ?, ?, ?)
        """, (
            id_cv,
            id_con,
            id_veiculo_sql,
            int(row["Sequencia"]) if pd.notna(row.get("Sequencia")) else None,
        ))
        if cur.rowcount:
            ins_cv += 1

    cur.execute("SELECT COUNT(*) FROM contrato_veiculo")
    print(f"  Inseridos: {ins_cv}  |  Total SQL: {cur.fetchone()[0]}")

    con.commit()

    # ── Verificação final ─────────────────────────────────────────────────────
    print("\nVerificação final:")
    for tbl in ["empresas", "clientes", "contratos", "contrato_veiculo"]:
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        cnt = cur.fetchone()[0]
        exp_xl = {
            "empresas":         len(df_emp),
            "clientes":         len(df_cli),
            "contratos":        len(df_con),
            "contrato_veiculo": len(df_cv),
        }[tbl]
        ok = "✓" if cnt == exp_xl else f"⚠ esperado {exp_xl}"
        print(f"  {tbl:<25s} {cnt:>4d}  {ok}")

    cur.execute("PRAGMA integrity_check")
    print(f"\n  integrity_check: {cur.fetchone()[0]}")

    con.close()
    print(f"\nFA4 concluído: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
