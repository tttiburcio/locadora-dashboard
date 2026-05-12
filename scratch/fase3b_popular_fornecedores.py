"""
FASE 3B — Script 2: Popular tabela fornecedores + aliases + vincular FK.
Idempotente: INSERT OR IGNORE. Não toca em dados existentes.
"""
import sqlite3, os, sys, io, unicodedata
from datetime import datetime
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")


def strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


def normalize_key(s: str) -> str:
    s = s.strip()
    s = " ".join(s.split())
    s = strip_accents(s).upper()
    return s


def is_multi(s: str) -> bool:
    return "/" in s


def main():
    print("=" * 70)
    print("FASE 3B — Script 2: Popular Fornecedores")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = OFF")
    cur = con.cursor()

    # Coleta todos os fornecedores únicos de ordens_servico (não deletados)
    cur.execute("""
        SELECT DISTINCT TRIM(fornecedor)
        FROM ordens_servico
        WHERE fornecedor IS NOT NULL AND TRIM(fornecedor) != ''
          AND deletado_em IS NULL
    """)
    todos = [r[0] for r in cur.fetchall()]
    print(f"Fornecedores únicos em ordens_servico: {len(todos)}")

    simples = [f for f in todos if not is_multi(f)]
    multis  = [f for f in todos if is_multi(f)]
    print(f"  Simples (sem '/'): {len(simples)}")
    print(f"  Multi (com '/'):   {len(multis)}")

    # Agrupa simples por chave normalizada (detecta alias de acentuação)
    grupos: dict[str, list[str]] = defaultdict(list)
    for f in simples:
        grupos[normalize_key(f)].append(f)

    # Para cada grupo: o canônico = o mais frequente (ou primeiro se empate)
    cur.execute("""
        SELECT TRIM(fornecedor), COUNT(*) as cnt
        FROM ordens_servico
        WHERE fornecedor IS NOT NULL AND TRIM(fornecedor) != ''
          AND deletado_em IS NULL
        GROUP BY TRIM(fornecedor)
    """)
    freq = {r[0]: r[1] for r in cur.fetchall()}

    canonicos_inseridos = 0
    aliases_inseridos   = 0

    print("\nInserindo fornecedores e aliases...")
    try:
        con.execute("BEGIN")

        for key, membros in grupos.items():
            membros_sorted = sorted(membros, key=lambda x: freq.get(x, 0), reverse=True)
            canonico = membros_sorted[0]

            cur.execute(
                "INSERT OR IGNORE INTO fornecedores (nome) VALUES (?)",
                (canonico,)
            )
            if cur.rowcount:
                canonicos_inseridos += 1

            # Busca id do canônico
            cur.execute("SELECT id FROM fornecedores WHERE nome = ?", (canonico,))
            row = cur.fetchone()
            if not row:
                continue
            forn_id = row[0]

            # Aliases = membros não-canônicos no mesmo grupo de normalização
            for alias in membros_sorted[1:]:
                cur.execute(
                    "INSERT OR IGNORE INTO fornecedor_aliases (fornecedor_id, alias, confianca) VALUES (?, ?, 'ALTA')",
                    (forn_id, alias)
                )
                if cur.rowcount:
                    aliases_inseridos += 1

        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise RuntimeError(f"Erro ao inserir fornecedores: {e}")

    print(f"  Fornecedores inseridos: {canonicos_inseridos}")
    print(f"  Aliases inseridos (ALTA): {aliases_inseridos}")

    # Vincula ordens_servico.fornecedor_id
    print("\nVinculando ordens_servico.fornecedor_id...")

    # Monta lookup: text → fornecedor_id (via nome ou alias)
    cur.execute("SELECT id, nome FROM fornecedores")
    lookup: dict[str, int] = {}
    for fid, nome in cur.fetchall():
        lookup[normalize_key(nome)] = fid

    cur.execute("SELECT fornecedor_id, alias FROM fornecedor_aliases")
    for fid, alias in cur.fetchall():
        lookup[normalize_key(alias)] = fid

    cur.execute("""
        SELECT id, TRIM(fornecedor) FROM ordens_servico
        WHERE fornecedor IS NOT NULL AND TRIM(fornecedor) != ''
          AND deletado_em IS NULL AND fornecedor_id IS NULL
    """)
    rows = cur.fetchall()

    vinculados = 0
    nao_vinculados = 0

    try:
        con.execute("BEGIN")
        for os_id, forn_text in rows:
            if is_multi(forn_text):
                nao_vinculados += 1
                continue
            key = normalize_key(forn_text)
            fid = lookup.get(key)
            if fid:
                cur.execute(
                    "UPDATE ordens_servico SET fornecedor_id = ? WHERE id = ? AND fornecedor_id IS NULL",
                    (fid, os_id)
                )
                if cur.rowcount:
                    vinculados += 1
            else:
                nao_vinculados += 1
        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise RuntimeError(f"Erro ao vincular FK: {e}")

    print(f"  Vinculados (fornecedor_id preenchido): {vinculados}")
    print(f"  Não vinculados (multi ou sem match):   {nao_vinculados}")

    # Resumo final
    cur.execute("SELECT COUNT(*) FROM fornecedores")
    total_forn = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM fornecedor_aliases")
    total_alias = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ordens_servico WHERE fornecedor_id IS NOT NULL AND deletado_em IS NULL")
    total_linked = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ordens_servico WHERE fornecedor_id IS NULL AND fornecedor IS NOT NULL AND deletado_em IS NULL")
    total_unlinked = cur.fetchone()[0]

    print(f"\nRESUMO:")
    print(f"  fornecedores.count:                {total_forn}")
    print(f"  fornecedor_aliases.count:          {total_alias}")
    print(f"  ordens_servico com FK preenchida:  {total_linked}")
    print(f"  ordens_servico sem FK (pendentes): {total_unlinked}")

    con.close()
    print("\nScript 2 concluído.")
    print("=" * 70)


if __name__ == "__main__":
    main()
