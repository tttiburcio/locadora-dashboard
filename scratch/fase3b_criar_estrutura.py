"""
FASE 3B — Script 1: Criar estrutura (10 novas tabelas + 4 colunas nullable).
Idempotente: usa IF NOT EXISTS e verifica colunas antes de ALTER TABLE.
"""
import sqlite3, os, shutil, sys, io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")

DDL_TABLES = [
    ("fornecedores", """
        CREATE TABLE IF NOT EXISTS fornecedores (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      VARCHAR(200) NOT NULL UNIQUE,
            tipo      VARCHAR(20),
            cnpj      VARCHAR(18),
            ativo     BOOLEAN DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("fornecedor_aliases", """
        CREATE TABLE IF NOT EXISTS fornecedor_aliases (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            fornecedor_id  INTEGER NOT NULL REFERENCES fornecedores(id),
            alias          VARCHAR(200) NOT NULL UNIQUE,
            confianca      VARCHAR(10) DEFAULT 'ALTA',
            criado_em      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("idx_forn_alias", """
        CREATE INDEX IF NOT EXISTS idx_forn_alias ON fornecedor_aliases(fornecedor_id)
    """),
    ("catalogo_servicos", """
        CREATE TABLE IF NOT EXISTS catalogo_servicos (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      VARCHAR(200) NOT NULL UNIQUE,
            sistema   VARCHAR(80),
            categoria VARCHAR(30),
            confianca VARCHAR(10),
            ativo     BOOLEAN DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("catalogo_aliases", """
        CREATE TABLE IF NOT EXISTS catalogo_aliases (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            servico_id INTEGER NOT NULL REFERENCES catalogo_servicos(id),
            alias      VARCHAR(200) NOT NULL UNIQUE,
            criado_em  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("idx_cat_alias", """
        CREATE INDEX IF NOT EXISTS idx_cat_alias ON catalogo_aliases(servico_id)
    """),
    ("catalogo_componentes", """
        CREATE TABLE IF NOT EXISTS catalogo_componentes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            servico_id INTEGER NOT NULL REFERENCES catalogo_servicos(id),
            componente VARCHAR(200) NOT NULL,
            unidade    VARCHAR(20),
            criado_em  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("pneu_medidas", """
        CREATE TABLE IF NOT EXISTS pneu_medidas (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            medida    VARCHAR(30) NOT NULL UNIQUE,
            aro       VARCHAR(10),
            largura   INTEGER,
            perfil    INTEGER,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("veiculo_pneu_compativel", """
        CREATE TABLE IF NOT EXISTS veiculo_pneu_compativel (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            frota_id  INTEGER NOT NULL REFERENCES frota(id),
            medida_id INTEGER NOT NULL REFERENCES pneu_medidas(id),
            eixo      VARCHAR(20),
            fonte     VARCHAR(20) DEFAULT 'historico',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(frota_id, medida_id)
        )
    """),
    ("idx_vpc_frota", """
        CREATE INDEX IF NOT EXISTS idx_vpc_frota ON veiculo_pneu_compativel(frota_id)
    """),
    ("catalogo_pneus", """
        CREATE TABLE IF NOT EXISTS catalogo_pneus (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            marca     VARCHAR(80) NOT NULL,
            modelo    VARCHAR(80),
            medida_id INTEGER REFERENCES pneu_medidas(id),
            ativo     BOOLEAN DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("idx_cat_pneu_medida", """
        CREATE INDEX IF NOT EXISTS idx_cat_pneu_medida ON catalogo_pneus(medida_id)
    """),
    ("pendencias_consolidacao", """
        CREATE TABLE IF NOT EXISTS pendencias_consolidacao (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo              VARCHAR(50) NOT NULL,
            tabela_origem     VARCHAR(50),
            registro_id       INTEGER,
            campo             VARCHAR(80),
            valor_sql         TEXT,
            valor_excel       TEXT,
            sugestao_sistema  TEXT,
            nivel_confianca   VARCHAR(10),
            status            VARCHAR(20) DEFAULT 'pendente',
            revisado_por      VARCHAR(50),
            revisado_em       TIMESTAMP,
            observacao        TEXT,
            criado_em         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """),
    ("idx_pend_status", """
        CREATE INDEX IF NOT EXISTS idx_pend_status ON pendencias_consolidacao(status)
    """),
    ("idx_pend_tipo", """
        CREATE INDEX IF NOT EXISTS idx_pend_tipo ON pendencias_consolidacao(tipo)
    """),
    ("consolidacao_log", """
        CREATE TABLE IF NOT EXISTS consolidacao_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            tabela        VARCHAR(50) NOT NULL,
            registro_id   INTEGER NOT NULL,
            campo         VARCHAR(80) NOT NULL,
            valor_antes   TEXT,
            valor_depois  TEXT,
            fonte         VARCHAR(20),
            regra         TEXT,
            conflito      VARCHAR(10),
            executado_em  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            executado_por VARCHAR(50)
        )
    """),
    ("idx_clog_tabela", """
        CREATE INDEX IF NOT EXISTS idx_clog_tabela ON consolidacao_log(tabela, registro_id)
    """),
]

ALTER_COLUMNS = [
    ("os_itens",       "fornecedor_id",        "INTEGER REFERENCES fornecedores(id)"),
    ("os_itens",       "servico_catalogo_id",   "INTEGER REFERENCES catalogo_servicos(id)"),
    ("os_itens",       "medida_pneu_id",        "INTEGER REFERENCES pneu_medidas(id)"),
    ("ordens_servico", "fornecedor_id",         "INTEGER REFERENCES fornecedores(id)"),
]

NEW_TABLES = {
    "fornecedores", "fornecedor_aliases", "catalogo_servicos", "catalogo_aliases",
    "catalogo_componentes", "pneu_medidas", "veiculo_pneu_compativel",
    "catalogo_pneus", "pendencias_consolidacao", "consolidacao_log",
}


def column_exists(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in cur.fetchall())


def main():
    print("=" * 70)
    print("FASE 3B — Script 1: Criar Estrutura")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"DB não encontrado: {DB_PATH}")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("PRAGMA integrity_check")
    ic = cur.fetchone()[0]
    if ic != "ok":
        con.close()
        raise RuntimeError(f"integrity_check falhou: {ic}")
    print("PRAGMA integrity_check: ok")

    created = 0
    skipped = 0
    for name, ddl in DDL_TABLES:
        try:
            cur.execute(ddl.strip())
            con.commit()
            if name in NEW_TABLES:
                created += 1
        except sqlite3.OperationalError as e:
            print(f"  AVISO {name}: {e}")
            skipped += 1

    print(f"DDL executado: {created} tabelas/índices criados, {skipped} avisos")

    added = 0
    for table, col, typedef in ALTER_COLUMNS:
        if not column_exists(cur, table, col):
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}")
            con.commit()
            print(f"  + ALTER TABLE {table} ADD COLUMN {col}")
            added += 1
        else:
            print(f"  [já existe] {table}.{col}")
    print(f"Colunas adicionadas: {added}")

    # Verificação
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
        "('fornecedores','fornecedor_aliases','catalogo_servicos','catalogo_aliases',"
        "'catalogo_componentes','pneu_medidas','veiculo_pneu_compativel',"
        "'catalogo_pneus','pendencias_consolidacao','consolidacao_log')"
    )
    tables_found = {r[0] for r in cur.fetchall()}
    missing = NEW_TABLES - tables_found
    if missing:
        print(f"ERRO — tabelas ausentes: {missing}")
    else:
        print(f"Verificação: 10/10 novas tabelas presentes.")

    con.close()
    print("Script 1 concluído.")
    print("=" * 70)


if __name__ == "__main__":
    main()
