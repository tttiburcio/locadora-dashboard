"""
FASE 3B.1 — Script 1: Expandir catálogo (novos aliases + novos grupos) e re-vincular FKs.
Idempotente: INSERT OR IGNORE. Zero remoção de dados.
"""
import sqlite3, os, sys, io, unicodedata
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")


def strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


def normalize_key(s: str) -> str:
    s = " ".join(s.strip().split())
    return strip_accents(s).upper()


# ── Novos aliases para grupos JÁ existentes ──────────────────────────────────
ALIASES_NOVOS: dict[str, list[str]] = {
    "Kit Revisão": [
        "KIT REVISAO — VW EXPRESS",          # em dash —
        "KIT REVISAO — VW 9150",
        "KIT REVISAO — VW 9170",
        "KIT REVISAO — VW 13-180",
        "KIT REVISAO — VW 14-190",
        "KIT REVISAO 500H — JCB 3CX",
        "KIT DE REVISÃO CAT 416F2",
        "FORNEC. FILTROS",
        "FORNEC. KIT FILTROS + ÓLEO",
        "FORNEC. ÓLEO + FILTRO",
        "FORNEC. KIT FILTROS",
        "FORNEC. KIT CORREIA + KIT REVISÃO",
        "KIT REVISAO — VW 9150",
        "REVISÃO GERAL",
        "REPARO CUBO DIANTEIRO",
        "REPARO VAZAMENTO ÓLEO + REVISÃO",
        "MO SUBST. SUSPENSÃO E COXIM",
    ],
    "Troca de Óleo e Filtros": [
        "Filtro de Ar",
        "Filtro de Combustível",
        "Filtro Lubrificante",
        "Filtro de Óleo",
        "Filtro de Ar Primário",
        "Filtro de Ar Secundário",
        "Filtro de Combustível Separador",
        "Filtro Raccor",
        "Filtro de Óleo Diesel",
        "FORNEC. FILTROS AR",
        "FORNEC. ÓLEO",
        "FORNEC. ÓLEO DE MOTOR",
        "FORNEC. ÓLEO MOTOR",
        "Óleo 15w40",
        "Óleo de Motor 15w40",
        "Óleo de Motor SAE 15w40",
        "Carter de Óleo de Motor",
        "Junta do Carter",
        "FORNEC. CORREIA POLI-V",
        "FORNEC. SENSOR MAP",
        "FORNEC. SENSOR RAIL",
        "FORNEC. SENSOR E ADITIVO",
        "FORNEC. SOLENOIDE",
    ],
    "Substituição de Pastilhas de Freio": [
        "SUBST. PASTILHAS E DISCOS",
        "FORNEC. PASTILHAS E DISCOS",
        "FORNEC. PASTILHAS E DISCO",
        "SUBST. PASTILHAS + REVISÃO",
        "RECOLOCAÇÃO PASTILHAS",
        "SUBST. PASTILHAS E PASSE DISCOS",
        "SUBST. PASTILHAS E REPARO CILINDRO",
        "SUBST. PASTILHAS, DISCOS E REPARO PINÇA",
        "SUBST. PASTILHAS DISCOS E CUBO TRASEIRO",
        "FORNEC. PINÇA DIANTEIRA",
        "FORNEC. PINÇA, DISCO E PASTILHAS",
        "FORNEC. PINÇA, DISCOS E PASTILHAS",
        "FORNEC. PINÇAS TRASEIRAS",
        "SUBST. PINÇA, DISCOS E PASTILHAS",
        "SUBST. PINÇAS TRASEIRAS",
        "FORNEC. DISCOS DE FREIO DIANTEIRO E TRASEIRO",
        "FORNEC. CILINDRO MESTRE DE FREIO",
        "FORNEC. PASTILHAS E DISCOS",
        "Fluído de Freio",
        "SUBST. PASTILHAS + REVISÃO",
        "Substituição de Cilindro Mestre de Freio",
    ],
    "Substituição de Lonas de Freio": [
        "MO SUBST. LONAS E PATIM",
        "SUBST. LONAS E CUÍCAS",
        "SUBST. LONAS E TAMBOR",
        "FORNEC. LONAS TRASEIRAS",
        "FORNEC. LONAS",
        "SUBST. CANO COMPRESSOR AR",
    ],
    "Kit Embreagem": [
        "M.O. KIT EMBREAGEM",
        "SUBST. KIT EMBREAGEM + RETÍFICA VOLANTE",
        "SUBST. KIT EMBREAGEM COMPLETO",
        "SUBSTITUIÇÃO DE KIT EMBREAGEM",
        "MO SUBST. SINCRONIZADOS E EMBREAGEM",
        "FORNEC. CILINDRO EMBREAGEM",
        "FORNEC. CABO DE EMBREAGEM",
        "FORNEC. ROLAMENTO EMBREAGEM",
        "Substituição Cabo de Embreagem",
        "FORNEC. FLUÍDO DE FREIO E CILINDRO MESTRE EMBREAGEM",
        "M.O. SUBSTITUIÇÃO DE EMBREAGEM VISCOSA E MANGUEIRA INTERCOOLER",
        "FORNEC. EMBREAGEM VISCOSA E MANGUEIRA INTERCOOLER",
        "LIMPEZA RADIADOR E INTERCOOLER",
        "REPARO MANGUEIRA RADIADOR",
    ],
    "Guincho / Socorro": [
        "REMOÇÃO VIA GUINCHO",
        "REMOÇÃO",
    ],
    "Montagem e Alinhamento de Pneus": [
        "INSTALAÇÃO PNEUS",
        "Alinhamento e Balanceamento",
        "Alinhamento Balanceamento e Cambagem",
        "SUBST. ROLAMENTO E BARRAS",
        "SUBST. BUCHAS, PIVÔS E BANDEJA",
        "SUBST. TERMINAIS DIREÇÃO",
        "SUBST. BOMBA HIDRÁULICA",
    ],
    "Serviço Elétrico": [
        "REPARO ELÉTRICO GERAL",
        "REPARO CHICOTE ELÉTRICO",
        "DIAGNÓSTICO ELÉTRICO",
        "REPARO CHICOTE E VÁLVULA",
        "REPARO MOTOR DE PARTIDA",
        "SUBST. AUTOMÁTICO M. PARTIDA",
        "SUBST. TRANSISTOR MÓDULO",
        "M.O. SUBSTITUIÇÃO CONVERSOR 12V E CONFERÊNCIA DE POSITIVO",
        "FORNEC. ECM BOSCH",
        "01 BATERIA 100A",
    ],
    "Fornecimento de Pneus": [
        "FORNEC. PNEU",
        "FORNEC. PNEUS RECAP",
        "PN 17.5-25 16PR G2/L2 TL",
        "FORNEC. PNEUS + MONTAGEM",
    ],
    "Balanceamento de Pneus": [
        "FORNEC. KIT CORREIA E FLUIDOS",
    ],
}

# ── Novos grupos canônicos ────────────────────────────────────────────────────
NOVOS_GRUPOS: list[tuple] = [
    (
        "Retífica / Reparo de Motor", "Motor", "Servico", "ALTA",
        [
            "RETÍFICA DE MOTOR COMPLETA",
            "RETÍFICA DE MOTOR COMPLETA (ADIANT.)",
            "RETÍFICA CABEÇOTE + VÁLVULAS",
            "RETÍFICA CABEÇOTE E BLOCO",
            "MO MONTAGEM CABEÇOTE",
            "FORNEC. KIT MOTOR BAIXO",
            "FORNEC. PEÇAS MOTOR BAIXO",
            "FORNEC. KIT REPARO MOTOR",
            "FORNEC. PEÇAS RETÍFICA CABEÇOTE",
            "Motor Parcial Completo",
            "SUBST. JUNTAS MOTOR",
            "SUBST. RESFRIADOR ÓLEO E PASTILHAS",
            "FORNEC. TURBINA",
            "Turbinas",
            "Recuperação de Rosca de Carter",
            "Substituição de Carter",
            "FORNEC. MANGUEIRA E COXINS",
            "FORNEC. PEÇAS (INDENIZAÇÃO)",
        ],
    ),
    (
        "Reparo de Câmbio", "Cambio", "Servico", "ALTA",
        [
            "MO SUBST. ENGRENAGENS CÂMBIO",
            "MO SUBST. PEÇAS CÂMBIO",
            "SUBST. PEÇAS CÂMBIO",
            "FORNEC. PEÇAS CÂMBIO",
            "FORNEC. PEÇAS CÂMBIO + ÓLEO",
            "Verificação Seletora de Marchas",
            "Filtro de Transmissão",
            "FORNEC. ÓLEO TRANSMISSÃO",
            "Óleo SAE 80w90",
            "FORNEC. CABOS CÂMBIO",
        ],
    ),
    (
        "Reparo de Direção", "Direcao", "Servico", "ALTA",
        [
            "REPARO CAIXA DIREÇÃO",
            "MO REPARO DIREÇÃO",
            "M.O. REPARO EM CAIXA DE DIREÇÃO, SOLDA E TROCA DE KIT",
            "KIT DE CAIXA DE DIREÇÃO",
            "REPARO CUBO E EMBUCHAMENTO DIREÇÃO",
            "FORNEC. BRAÇO AXIAL DIREÇÃO",
            "FORNEC. PEÇAS DIREÇÃO E CABINE",
        ],
    ),
    (
        "Suspensão", "Suspensao", "Servico", "ALTA",
        [
            "SUBST. AMORTECEDORES",
            "M.O. EMBUCHAMENTO DE MOLEJOS TRASEIROS",
            "Substituição de Amortecedor Dianteiro",
            "Substituição de Mola Mestre Dianteira",
            "Amortecedor Dianteiro",
            "Mola Dianteira",
        ],
    ),
    (
        "Reparo Hidráulico", "Hidraulico", "Servico", "ALTA",
        [
            "REPARO BOMBA HIDRÁULICA",
            "SUBST. BOMBA HID. E TDF",
            "SUBST. MANGUEIRA HIDRÁULICA",
            "REPARO PISTÃO HIDRÁULICO",
            "SUBST. MANGUEIRA TELESCÓPIO",
            "SUBST. NIPLE TELESCÓPIO",
            "SUBST. CREMALHEIRA E COLUNA",
            "FORNEC. MANGUEIRA HIDRÁULICA",
            "MANGUEIRA DE ALTA PRESSÃO",
            "FORNEC. BOMBA HIDRÁULICA",
            "FORNEC. ÓLEO HIDRÁULICO",
            "FORNEC. RESERVATÓRIO DIREÇÃO",
            "Filtro Hidráulico",
        ],
    ),
    (
        "Funilaria / Pintura", "Diversos", "Servico", "ALTA",
        [
            "PINTURA PARACHOQUE TRASEIRO",
            "PINTURA PARACHOQUE E CARROCERIA",
            "FUNILARIA GERAL",
            "PINTURA PARACHOQUE E CARROCERIA",
        ],
    ),
    (
        "Diagnóstico / Scanner", "Motor", "Servico", "ALTA",
        [
            "DIAGNÓSTICO SCANNER",
            "RECONDICIONAMENTO INJEÇÃO ELETRÔNICA",
            "MO ANÁLISE VAZAMENTO",
        ],
    ),
    (
        "Fornecimento de Bateria", "Eletrico", "Compra", "ALTA",
        [
            "FORNEC. BATERIA",
            "FORNEC. CONVERSOR",
            "FORNEC. ROTOR M. PARTIDA",
        ],
    ),
]


def main():
    print("=" * 70)
    print("FASE 3B.1 — Script 1: Expandir Catálogo")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = OFF")
    cur = con.cursor()

    # Snapshot antes
    cur.execute("SELECT COUNT(*) FROM os_itens WHERE servico_catalogo_id IS NOT NULL")
    cobertura_antes = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM catalogo_aliases")
    aliases_antes = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM catalogo_servicos")
    grupos_antes = cur.fetchone()[0]
    print(f"Estado inicial: {cobertura_antes}/310 os_itens vinculados, {grupos_antes} grupos, {aliases_antes} aliases")

    # ── 1. Novos aliases para grupos existentes ──────────────────────────────
    print("\n[1] Adicionando aliases a grupos existentes...")
    aliases_adicionados = 0
    aliases_colisoes = 0

    try:
        con.execute("BEGIN")
        for grupo_nome, aliases in ALIASES_NOVOS.items():
            cur.execute("SELECT id FROM catalogo_servicos WHERE nome = ?", (grupo_nome,))
            row = cur.fetchone()
            if not row:
                print(f"  AVISO: grupo '{grupo_nome}' não encontrado — pulando")
                continue
            srv_id = row[0]
            for alias in aliases:
                cur.execute(
                    "INSERT OR IGNORE INTO catalogo_aliases (servico_id, alias) VALUES (?, ?)",
                    (srv_id, alias),
                )
                if cur.rowcount:
                    aliases_adicionados += 1
                else:
                    # Verify if alias is for a DIFFERENT service (collision)
                    cur.execute("SELECT servico_id FROM catalogo_aliases WHERE alias = ?", (alias,))
                    existing = cur.fetchone()
                    if existing and existing[0] != srv_id:
                        aliases_colisoes += 1
        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise RuntimeError(f"Erro ao adicionar aliases: {e}")

    print(f"  Aliases adicionados: {aliases_adicionados}")
    if aliases_colisoes:
        print(f"  Colisões detectadas (alias já existe em outro grupo): {aliases_colisoes}")

    # ── 2. Novos grupos canônicos ────────────────────────────────────────────
    print("\n[2] Criando novos grupos canônicos...")
    grupos_criados = 0
    aliases_novos_grupos = 0

    try:
        con.execute("BEGIN")
        for nome, sistema, categoria, confianca, aliases in NOVOS_GRUPOS:
            cur.execute(
                "INSERT OR IGNORE INTO catalogo_servicos (nome, sistema, categoria, confianca) VALUES (?, ?, ?, ?)",
                (nome, sistema, categoria, confianca),
            )
            if cur.rowcount:
                grupos_criados += 1

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
                    aliases_novos_grupos += 1

        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise RuntimeError(f"Erro ao criar novos grupos: {e}")

    print(f"  Novos grupos criados: {grupos_criados}")
    print(f"  Aliases para novos grupos: {aliases_novos_grupos}")

    # ── 3. Re-vincular os_itens.servico_catalogo_id ──────────────────────────
    print("\n[3] Re-vinculando os_itens.servico_catalogo_id...")

    # Rebuild lookup
    lookup: dict[str, int] = {}
    cur.execute("SELECT id, nome FROM catalogo_servicos")
    for sid, nome in cur.fetchall():
        lookup[normalize_key(nome)] = sid

    cur.execute("""
        SELECT ca.servico_id, ca.alias
        FROM catalogo_aliases ca
    """)
    for sid, alias in cur.fetchall():
        lookup[normalize_key(alias)] = sid

    # Link unmatched items
    cur.execute("""
        SELECT id, servico FROM os_itens
        WHERE servico IS NOT NULL AND servico_catalogo_id IS NULL
    """)
    rows = cur.fetchall()

    vinculados_novos = 0
    sem_match = 0

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
                    vinculados_novos += 1
            else:
                sem_match += 1
        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise RuntimeError(f"Erro ao vincular FKs: {e}")

    print(f"  Novos vínculos criados: {vinculados_novos}")
    print(f"  Ainda sem match: {sem_match}")

    # ── Resumo ────────────────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM os_itens WHERE servico_catalogo_id IS NOT NULL")
    cobertura_depois = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM catalogo_aliases")
    aliases_depois = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM catalogo_servicos")
    grupos_depois = cur.fetchone()[0]

    print(f"\nRESUMO:")
    print(f"  Grupos canônicos: {grupos_antes} → {grupos_depois} (+{grupos_depois-grupos_antes})")
    print(f"  Aliases totais:   {aliases_antes} → {aliases_depois} (+{aliases_depois-aliases_antes})")
    print(f"  Cobertura FK:     {cobertura_antes}/310 → {cobertura_depois}/310 "
          f"({round(100*cobertura_antes/310)}% → {round(100*cobertura_depois/310)}%)")

    # Breakdown por sistema
    print("\n  Cobertura por sistema:")
    cur.execute("""
        SELECT sistema, COUNT(*) total, COUNT(servico_catalogo_id) com_fk
        FROM os_itens
        WHERE servico IS NOT NULL
        GROUP BY sistema ORDER BY sistema
    """)
    for sis, total, com in cur.fetchall():
        pct = round(100*com/total) if total else 0
        print(f"    {str(sis):<20s} {com:3d}/{total:3d} ({pct:3d}%)")

    con.close()
    print("\nScript 1 concluído.")
    print("=" * 70)


if __name__ == "__main__":
    main()
