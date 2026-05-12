"""
FASE 3B.1 — Script 2: Atualizar pendências após expansão do catálogo.
- Fecha pendências servico_sem_grupo onde FK já foi preenchida.
- Enriquece sugestao_sistema para pendências restantes.
Idempotente.
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
    return strip_accents(" ".join(s.strip().split())).upper()


# Palavras-chave para sugerir grupo nas pendências restantes
SUGESTAO_KEYWORDS: list[tuple[str, str]] = [
    ("IMPLEMENTO",    "Verificar: serviço de implemento/carroceria — criar grupo 'Serviço de Implemento'?"),
    ("SOLDA",         "Verificar: serviço de solda — criar grupo 'Solda / Funilaria'?"),
    ("DIFERENCIAL",   "Verificar: reparo de diferencial — criar grupo 'Reparo de Diferencial'?"),
    ("INJEÇÃO",       "Verificar: sistema de injeção — criar grupo 'Diagnóstico / Injeção'?"),
    ("SCANNER",       "Verificar: diagnóstico — vincular a 'Diagnóstico / Scanner'?"),
    ("FAIXAS",        "Verificar: faixas refletivas — Compra diversa"),
    ("FRETE",         "Verificar: frete — Custo operacional, não manutenção"),
    ("ARREFECIMENTO", "Verificar: arrefecimento — criar grupo 'Reparo Arrefecimento'?"),
    ("RADIADOR",      "Verificar: arrefecimento — criar grupo 'Reparo Arrefecimento'?"),
    ("INTERCOOLER",   "Verificar: arrefecimento — criar grupo 'Reparo Arrefecimento'?"),
    ("REEMISSÃO",     "Verificar: burocrático — não é manutenção técnica"),
    ("PLACA",         "Verificar: burocrático — não é manutenção técnica"),
]


def main():
    print("=" * 70)
    print("FASE 3B.1 — Script 2: Atualizar Pendências")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = OFF")
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM pendencias_consolidacao WHERE tipo='servico_sem_grupo' AND status='pendente'")
    antes = cur.fetchone()[0]
    print(f"Pendências servico_sem_grupo antes: {antes}")

    # ── 1. Fechar pendências onde os_itens já tem servico_catalogo_id ─────────
    print("\n[1] Fechando pendências resolvidas pela expansão do catálogo...")
    cur.execute("""
        SELECT pc.id, pc.registro_id
        FROM pendencias_consolidacao pc
        JOIN os_itens oi ON oi.id = pc.registro_id
        WHERE pc.tipo = 'servico_sem_grupo'
          AND pc.status = 'pendente'
          AND oi.servico_catalogo_id IS NOT NULL
    """)
    resolvidas = cur.fetchall()

    fechadas = 0
    if resolvidas:
        try:
            con.execute("BEGIN")
            ids = [r[0] for r in resolvidas]
            placeholders = ",".join("?" * len(ids))
            cur.execute(
                f"""UPDATE pendencias_consolidacao
                    SET status='resolvido', revisado_em=CURRENT_TIMESTAMP,
                        revisado_por='fase3b1_auto', observacao='Resolvido automaticamente — servico_catalogo_id preenchido'
                    WHERE id IN ({placeholders})""",
                ids,
            )
            fechadas = cur.rowcount
            con.commit()
        except Exception as e:
            con.rollback()
            con.close()
            raise RuntimeError(f"Erro ao fechar pendências: {e}")

    print(f"  Pendências fechadas (resolvidas): {fechadas}")

    # ── 2. Enriquecer sugestao_sistema nas pendências restantes ──────────────
    print("\n[2] Enriquecendo sugestão nas pendências restantes...")
    cur.execute("""
        SELECT pc.id, pc.valor_sql, oi.sistema, oi.categoria
        FROM pendencias_consolidacao pc
        LEFT JOIN os_itens oi ON oi.id = pc.registro_id
        WHERE pc.tipo = 'servico_sem_grupo'
          AND pc.status = 'pendente'
          AND (pc.sugestao_sistema IS NULL OR pc.sugestao_sistema = '')
    """)
    pendentes = cur.fetchall()

    enriquecidas = 0
    try:
        con.execute("BEGIN")
        for pend_id, valor_sql, sistema, categoria in pendentes:
            if not valor_sql:
                continue
            texto_upper = normalize_key(valor_sql)
            sugestao = None
            for kw, msg in SUGESTAO_KEYWORDS:
                if normalize_key(kw) in texto_upper:
                    sugestao = msg
                    break
            if not sugestao:
                sugestao = f"sistema={sistema}, categoria={categoria} — análise manual necessária"
            cur.execute(
                "UPDATE pendencias_consolidacao SET sugestao_sistema=? WHERE id=? AND (sugestao_sistema IS NULL OR sugestao_sistema='')",
                (sugestao, pend_id),
            )
            if cur.rowcount:
                enriquecidas += 1
        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise RuntimeError(f"Erro ao enriquecer pendências: {e}")

    print(f"  Pendências enriquecidas com sugestão: {enriquecidas}")

    # ── 3. Resumo final ───────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM pendencias_consolidacao WHERE tipo='servico_sem_grupo' AND status='pendente'")
    depois = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM pendencias_consolidacao WHERE tipo='servico_sem_grupo' AND status='resolvido'")
    resolvidas_total = cur.fetchone()[0]

    print(f"\nRESUMO pendencias_consolidacao (servico_sem_grupo):")
    print(f"  Antes:     {antes}")
    print(f"  Fechadas:  {fechadas}")
    print(f"  Restantes: {depois}")
    print(f"  Total resolvidas acumulado: {resolvidas_total}")

    # Resumo geral de todas as pendências
    print(f"\nTodas as pendências:")
    cur.execute("""
        SELECT tipo, status, COUNT(*) FROM pendencias_consolidacao
        GROUP BY tipo, status ORDER BY tipo, status
    """)
    for tipo, status, cnt in cur.fetchall():
        print(f"  {tipo:<35s} {status:<12s} {cnt}")

    con.close()
    print("\nScript 2 concluído.")
    print("=" * 70)


if __name__ == "__main__":
    main()
