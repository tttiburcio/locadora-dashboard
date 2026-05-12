"""
FASE FINAL — FA1: Criar tabelas SQL e adicionar colunas faltantes.
Idempotente (CREATE TABLE IF NOT EXISTS / ALTER TABLE IF NOT EXISTS).
"""
import sqlite3, os, sys, io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")

TABELAS = [
    # reembolsos já existe de fase anterior — só criar se não existir (sem as colunas extras)
    ("reembolsos", """
        CREATE TABLE IF NOT EXISTS reembolsos (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            emissao          DATE,
            id_veiculo       INTEGER REFERENCES frota(id),
            valor_reembolso  NUMERIC(14,2)
        )
    """),
    ("faturamento_mensal", """
        CREATE TABLE IF NOT EXISTS faturamento_mensal (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            id_fatura_excel     INTEGER UNIQUE,
            emissao             DATE NOT NULL,
            vencimento          DATE,
            valor_locacoes      REAL DEFAULT 0,
            valor_recebido      REAL DEFAULT 0,
            status_recebimento  TEXT,
            empresa             TEXT,
            id_contrato_excel   TEXT,
            id_cliente_excel    INTEGER,
            origem              TEXT DEFAULT 'excel_legado',
            criado_em           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("empresas", """
        CREATE TABLE IF NOT EXISTS empresas (
            id         INTEGER PRIMARY KEY,
            nome       TEXT NOT NULL,
            cnpj_cpf   TEXT,
            municipio  TEXT,
            estado     TEXT,
            criado_em  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("clientes", """
        CREATE TABLE IF NOT EXISTS clientes (
            id             INTEGER PRIMARY KEY,
            nome           TEXT NOT NULL,
            cnpj_cpf       TEXT,
            municipio      TEXT,
            estado         TEXT,
            status_cliente TEXT,
            criado_em      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("contratos", """
        CREATE TABLE IF NOT EXISTS contratos (
            id               INTEGER PRIMARY KEY,
            empresa_id       INTEGER REFERENCES empresas(id),
            cliente_id       INTEGER REFERENCES clientes(id),
            nome_cliente     TEXT,
            cidade_operacao  TEXT,
            estado_operacao  TEXT,
            data_inicio      DATE,
            data_fim         DATE,
            data_encerramento DATE,
            status_contrato  TEXT,
            criado_em        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("contrato_veiculo", """
        CREATE TABLE IF NOT EXISTS contrato_veiculo (
            id           INTEGER PRIMARY KEY,
            contrato_id  INTEGER NOT NULL REFERENCES contratos(id),
            id_veiculo   INTEGER REFERENCES frota(id),
            sequencia    INTEGER,
            criado_em    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
]

COLUNAS_FROTA = [
    ("ano_modelo",      "TEXT"),
    ("tabela_fipe",     "REAL"),
    ("valor_implemento","REAL"),
]

COLUNAS_ORDENS_SERVICO = [
    ("origem",          "TEXT"),
    ("numero_os",       None),   # já existe, apenas verificar
]


def main():
    print("=" * 70)
    print("FASE FINAL — FA1: Criar tabelas SQL")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # ── Tabelas novas ──────────────────────────────────────────────────────────
    print("\n[1] Criando tabelas novas...")
    for nome, ddl in TABELAS:
        cur.execute(ddl)
        cur.execute(f"SELECT COUNT(*) FROM {nome}")
        cnt = cur.fetchone()[0]
        print(f"  {nome:<30s} ok  ({cnt} registros)")

    # ── Colunas extras em reembolsos (tabela já existia de fase anterior) ─────
    print("\n[2] Adicionando colunas extras a reembolsos (se não existirem)...")
    cur.execute("PRAGMA table_info(reembolsos)")
    cols_reimb = {r[1] for r in cur.fetchall()}
    colunas_reimb_extras = [
        ("placa",              "TEXT"),
        ("vencimento",         "DATE"),
        ("empresa",            "TEXT"),
        ("valor_recebido",     "REAL"),
        ("status_recebimento", "TEXT"),
        ("tipo",               "TEXT"),
        ("id_contrato_excel",  "INTEGER"),
        ("id_cliente_excel",   "INTEGER"),
        ("origem",             "TEXT"),
    ]
    for col, tipo in colunas_reimb_extras:
        if col not in cols_reimb:
            cur.execute(f"ALTER TABLE reembolsos ADD COLUMN {col} {tipo}")
            print(f"  reembolsos.{col} ({tipo}) — ADICIONADA")
        else:
            print(f"  reembolsos.{col} — já existe")

    # ── Colunas frota ──────────────────────────────────────────────────────────
    print("\n[3] Adicionando colunas a frota (se não existirem)...")
    cur.execute("PRAGMA table_info(frota)")
    colunas_existentes = {r[1] for r in cur.fetchall()}
    for col, tipo in COLUNAS_FROTA:
        if col not in colunas_existentes:
            cur.execute(f"ALTER TABLE frota ADD COLUMN {col} {tipo}")
            print(f"  frota.{col} ({tipo}) — ADICIONADA")
        else:
            print(f"  frota.{col} — já existe")

    # ── Coluna origem em ordens_servico ───────────────────────────────────────
    print("\n[4] Adicionando coluna origem a ordens_servico (se não existir)...")
    cur.execute("PRAGMA table_info(ordens_servico)")
    os_cols = {r[1] for r in cur.fetchall()}
    if "origem" not in os_cols:
        cur.execute("ALTER TABLE ordens_servico ADD COLUMN origem TEXT")
        print("  ordens_servico.origem — ADICIONADA")
    else:
        print("  ordens_servico.origem — já existe")

    # ── Índice único em numero_os para idempotência FB ────────────────────────
    print("\n[5] Criando índice único em ordens_servico.numero_os (se não existir)...")
    cur.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND tbl_name='ordens_servico' AND name='uq_ordens_servico_numero_os'
    """)
    if not cur.fetchone():
        try:
            cur.execute("""
                CREATE UNIQUE INDEX uq_ordens_servico_numero_os
                ON ordens_servico(numero_os)
                WHERE numero_os IS NOT NULL
            """)
            print("  índice uq_ordens_servico_numero_os — CRIADO")
        except Exception as e:
            print(f"  aviso — não foi possível criar índice único: {e}")
    else:
        print("  índice uq_ordens_servico_numero_os — já existe")

    con.commit()

    # ── Verificação final ─────────────────────────────────────────────────────
    print("\n[6] Verificação final:")
    for nome, _ in TABELAS:
        cur.execute(f"SELECT COUNT(*) FROM {nome}")
        print(f"  {nome:<30s} {cur.fetchone()[0]}")

    cur.execute("PRAGMA table_info(frota)")
    cols_frota = [r[1] for r in cur.fetchall()]
    print(f"  frota colunas: {cols_frota}")

    cur.execute("PRAGMA integrity_check")
    print(f"\n  integrity_check: {cur.fetchone()[0]}")

    con.close()
    print(f"\nFA1 concluído: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
