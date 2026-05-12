"""
FASE 3B — Script 3: Popular catálogo de serviços + aliases + vincular FK.
Idempotente: INSERT OR IGNORE.
"""
import sqlite3, os, sys, io, unicodedata
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")

# Catálogo canônico: (nome, sistema, categoria, confianca, [aliases])
CATALOGO = [
    (
        "Fornecimento de Pneus", "Pneu", "Compra", "ALTA",
        [
            "FORNEC. PNEUS", "FORNEC PNEUS", "FORNECIMENTO PNEUS",
            "FORNECIMENTO DE PNEUS", "PNEU", "PNEUS",
            "FORNECIMENTO PNEU", "FORNEC PNEU",
        ],
    ),
    (
        "Montagem e Alinhamento de Pneus", "Pneu", "Servico", "ALTA",
        [
            "MONTAGEM E ALINHAMENTO PNEUS", "M.O. PNEUS", "M.O PNEUS",
            "ALINHAMENTO PNEUS", "MONTAGEM PNEUS", "MO PNEUS",
            "MONTAGEM E ALINHAMENTO DE PNEUS", "ALINHAMENTO E MONTAGEM PNEUS",
            "ALINHAMENTO E CAMBAGEM",
        ],
    ),
    (
        "Balanceamento de Pneus", "Pneu", "Servico", "ALTA",
        [
            "MONTAGEM E BALANCEAMENTO PNEUS", "INSTALAÇÃO E BALANCEAMENTO PNEUS",
            "BALANCEAMENTO PNEUS", "BALANCEAMENTO DE PNEUS",
            "INSTALACAO E BALANCEAMENTO PNEUS", "MONTAGEM BALANCEAMENTO PNEUS",
        ],
    ),
    (
        "Substituição de Pastilhas de Freio", "Freio", "Compra", "ALTA",
        [
            "SUBST. PASTILHAS", "SUBST. PASTILHAS DE FREIO",
            "SUBSTITUIÇÃO DE PASTILHAS", "SUBST. PASTILHAS FREIO",
            "PASTILHAS DE FREIO", "PASTILHAS FREIO",
        ],
    ),
    (
        "Substituição de Lonas de Freio", "Freio", "Compra", "ALTA",
        [
            "SUBST. LONAS", "LONAS DE FREIO", "SUBST. LONAS DE FREIO",
            "SUBSTITUIÇÃO DE LONAS", "LONAS FREIO", "LONA DE FREIO",
        ],
    ),
    (
        "Kit Revisão", "Revisao", "Compra", "ALTA",
        [
            "KIT REVISAO VW EXPRESS", "KIT REVISAO SPRINTER", "KIT REVISAO VW",
            "KIT DE REVISAO", "KIT REVISAO", "KIT REVISÃO",
            "KIT REVISAO IVECO", "KIT REVISAO MERCEDES",
        ],
    ),
    (
        "Kit Embreagem", "Cambio", "Compra", "ALTA",
        [
            "FORNEC. KIT EMBREAGEM", "SUBST. KIT EMBREAGEM", "KIT DE EMBREAGEM",
            "KIT EMBREAGEM", "EMBREAGEM",
            "MÃO DE OBRA SUBSTITUIÇÃO DE EMBREAGEM",
            "MAO DE OBRA SUBSTITUICAO DE EMBREAGEM",
        ],
    ),
    (
        "Guincho / Socorro", "Guincho", "Servico", "ALTA",
        [
            "SOCORRO", "REBOQUE", "GUINCHO EMERGÊNCIA", "GUINCHO EMERGENCIA",
            "GUINCHO", "SOCORRO MECANICO", "REBOQUE / SOCORRO",
        ],
    ),
    (
        "Serviço Elétrico", "Eletrico", "Servico", "ALTA",
        [
            "SUBST. LÂMPADA", "SUBST. LAMPADA", "ELÉTRICA GERAL",
            "ELETRICA GERAL", "SERVICO ELETRICO", "SERVIÇO ELÉTRICO",
            "ELETRICO", "ELÉTRICO",
        ],
    ),
    (
        "Troca de Óleo e Filtros", "Motor", "Compra", "ALTA",
        [
            "TROCA OLEO", "ÓLEO + FILTROS", "OLEO + FILTROS",
            "TROCA DE OLEO", "TROCA DE ÓLEO",
            "OLEO E FILTROS", "ÓLEO E FILTROS",
            "TROCA DE ÓLEO E FILTROS", "TROCA OLEO E FILTROS",
        ],
    ),
]


def normalize_key(s: str) -> str:
    nfkd = unicodedata.normalize("NFD", s)
    s2 = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return " ".join(s2.upper().split())


def main():
    print("=" * 70)
    print("FASE 3B — Script 3: Popular Catálogo de Serviços")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = OFF")
    cur = con.cursor()

    # Insere serviços canônicos
    servicos_inseridos = 0
    aliases_inseridos  = 0

    try:
        con.execute("BEGIN")
        for nome, sistema, categoria, confianca, aliases in CATALOGO:
            cur.execute(
                "INSERT OR IGNORE INTO catalogo_servicos (nome, sistema, categoria, confianca) VALUES (?, ?, ?, ?)",
                (nome, sistema, categoria, confianca),
            )
            if cur.rowcount:
                servicos_inseridos += 1

            cur.execute("SELECT id FROM catalogo_servicos WHERE nome = ?", (nome,))
            row = cur.fetchone()
            if not row:
                continue
            srv_id = row[0]

            for alias in aliases:
                cur.execute(
                    "INSERT OR IGNORE INTO catalogo_aliases (servico_id, alias) VALUES (?, ?)",
                    (srv_id, alias),
                )
                if cur.rowcount:
                    aliases_inseridos += 1

        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise RuntimeError(f"Erro ao inserir catálogo: {e}")

    print(f"  Serviços inseridos: {servicos_inseridos} (de {len(CATALOGO)} no catálogo)")
    print(f"  Aliases inseridos:  {aliases_inseridos}")

    # Monta lookup alias normalizado → servico_id
    cur.execute("SELECT cs.id, ca.alias FROM catalogo_aliases ca JOIN catalogo_servicos cs ON cs.id = ca.servico_id")
    lookup: dict[str, int] = {}
    for sid, alias in cur.fetchall():
        lookup[normalize_key(alias)] = sid

    cur.execute("SELECT id, nome FROM catalogo_servicos")
    for sid, nome in cur.fetchall():
        lookup[normalize_key(nome)] = sid

    # Vincula os_itens.servico_catalogo_id
    print("\nVinculando os_itens.servico_catalogo_id...")
    cur.execute("""
        SELECT id, servico FROM os_itens
        WHERE servico IS NOT NULL AND servico_catalogo_id IS NULL
    """)
    rows = cur.fetchall()

    vinculados = 0
    try:
        con.execute("BEGIN")
        for item_id, servico_text in rows:
            key = normalize_key(servico_text)
            sid = lookup.get(key)
            if sid:
                cur.execute(
                    "UPDATE os_itens SET servico_catalogo_id = ? WHERE id = ? AND servico_catalogo_id IS NULL",
                    (sid, item_id),
                )
                if cur.rowcount:
                    vinculados += 1
        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise RuntimeError(f"Erro ao vincular FK: {e}")

    print(f"  os_itens vinculados: {vinculados}")

    cur.execute("SELECT COUNT(*) FROM os_itens WHERE servico_catalogo_id IS NULL AND servico IS NOT NULL")
    sem_match = cur.fetchone()[0]
    print(f"  os_itens sem match no catálogo: {sem_match}")

    # Resumo
    cur.execute("SELECT COUNT(*) FROM catalogo_servicos")
    total_srv = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM catalogo_aliases")
    total_ali = cur.fetchone()[0]

    print(f"\nRESUMO:")
    print(f"  catalogo_servicos.count: {total_srv}")
    print(f"  catalogo_aliases.count:  {total_ali}")
    print(f"  os_itens vinculados:     {vinculados}")
    print(f"  os_itens sem match:      {sem_match}")

    con.close()
    print("\nScript 3 concluído.")
    print("=" * 70)


if __name__ == "__main__":
    main()
