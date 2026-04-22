from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "locadora.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Cria todas as tabelas se não existirem. Importe models antes de chamar."""
    Base.metadata.create_all(bind=engine)
    _migrate_add_columns()


def _migrate_add_columns():
    """Adiciona colunas novas em tabelas existentes (idempotente)."""
    migrations = [
        ("os_itens",       "categoria",          "VARCHAR(30)"),
        ("ordens_servico", "status_execucao",     "VARCHAR(40)"),
        ("ordens_servico", "descricao_pendente",  "TEXT"),
        ("notas_fiscais",  "empresa_faturada",    "VARCHAR(100)"),
    ]
    with engine.connect() as conn:
        for table, column, col_type in migrations:
            try:
                conn.execute(
                    __import__("sqlalchemy").text(
                        f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
                    )
                )
                conn.commit()
            except Exception:
                pass  # coluna já existe
