"""
FASE 3B.1 — Script 3: Relatório de cobertura antes/depois.
Somente leitura. Gera scratch/relatorio_fase3b1_<timestamp>.txt
"""
import sqlite3, os, sys, io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")
SCRATCH = os.path.dirname(os.path.abspath(__file__))

# Baseline pré-3B.1 (estado pós-3B)
BASELINE = {
    "os_itens_total":       310,
    "com_servico_fk":        59,
    "grupos_canonicos":      10,
    "aliases_total":         74,
    "pendencias_sem_grupo": 251,
}


def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(SCRATCH, f"relatorio_fase3b1_{ts}.txt")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    lines = []

    def w(*args):
        lines.append(" ".join(str(a) for a in args))

    w("=" * 80)
    w("RELATÓRIO FASE 3B.1 — COBERTURA ANTES/DEPOIS")
    w(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    w("=" * 80)

    # ── Contagens gerais ──────────────────────────────────────────────────────
    w("\n── CONTAGENS ORIGINAIS (integridade) ────────────────────────────────────────")
    for table, exp in [("os_itens", 310), ("ordens_servico", 212)]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        cnt = cur.fetchone()[0]
        ok = "✓" if cnt == exp else f"⚠ ESPERADO {exp}"
        w(f"  {table:<30s} {cnt}  {ok}")

    # ── Catálogo de serviços ──────────────────────────────────────────────────
    w("\n── CATÁLOGO DE SERVIÇOS ─────────────────────────────────────────────────────")
    cur.execute("SELECT COUNT(*) FROM catalogo_servicos")
    grupos_atual = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM catalogo_aliases")
    aliases_atual = cur.fetchone()[0]

    w(f"  Grupos canônicos: {BASELINE['grupos_canonicos']} → {grupos_atual} (+{grupos_atual - BASELINE['grupos_canonicos']})")
    w(f"  Aliases totais:   {BASELINE['aliases_total']} → {aliases_atual} (+{aliases_atual - BASELINE['aliases_total']})")

    w("\n  Grupos e sua cobertura:")
    cur.execute("""
        SELECT cs.nome, cs.sistema, cs.categoria, COUNT(oi.id) as cnt
        FROM catalogo_servicos cs
        LEFT JOIN os_itens oi ON oi.servico_catalogo_id = cs.id
        GROUP BY cs.id ORDER BY cnt DESC, cs.nome
    """)
    for nome, sis, cat, cnt in cur.fetchall():
        w(f"    {nome:<45s} {str(sis):<12s} {str(cat):<10s} {cnt:5d} itens")

    # ── Cobertura geral ───────────────────────────────────────────────────────
    w("\n── COBERTURA servico_catalogo_id ────────────────────────────────────────────")
    cur.execute("SELECT COUNT(*) FROM os_itens WHERE servico_catalogo_id IS NOT NULL")
    com_fk = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM os_itens WHERE servico_catalogo_id IS NULL AND servico IS NOT NULL")
    sem_fk = cur.fetchone()[0]

    pct_antes = round(100 * BASELINE["com_servico_fk"] / BASELINE["os_itens_total"])
    pct_depois = round(100 * com_fk / BASELINE["os_itens_total"])

    w(f"  Antes:  {BASELINE['com_servico_fk']}/310 ({pct_antes}%)")
    w(f"  Depois: {com_fk}/310 ({pct_depois}%)")
    w(f"  Ganho:  +{com_fk - BASELINE['com_servico_fk']} os_itens vinculados (+{pct_depois - pct_antes}pp)")
    w(f"  Ainda sem match: {sem_fk}")

    # ── Cobertura por sistema ─────────────────────────────────────────────────
    w("\n── COBERTURA POR SISTEMA ────────────────────────────────────────────────────")
    cur.execute("""
        SELECT COALESCE(sistema, 'NULL'), categoria,
               COUNT(*) total,
               COUNT(servico_catalogo_id) com_fk
        FROM os_itens
        WHERE servico IS NOT NULL
        GROUP BY sistema, categoria
        ORDER BY sistema, categoria
    """)
    rows = cur.fetchall()
    w(f"  {'Sistema':<20s} {'Categoria':<12s} {'Com FK':>8s} {'Total':>6s} {'%':>6s}")
    w(f"  {'-'*20} {'-'*12} {'-'*8} {'-'*6} {'-'*6}")
    for sis, cat, total, com in rows:
        pct = round(100*com/total) if total else 0
        w(f"  {sis:<20s} {str(cat):<12s} {com:>8d} {total:>6d} {pct:>5d}%")

    # ── Serviços ainda sem match ──────────────────────────────────────────────
    w("\n── SERVIÇOS AINDA SEM MATCH (top 30 por frequência) ─────────────────────────")
    cur.execute("""
        SELECT oi.servico, COALESCE(oi.sistema,'NULL'), COALESCE(oi.categoria,'NULL'), COUNT(*) cnt
        FROM os_itens oi
        WHERE oi.servico_catalogo_id IS NULL
          AND oi.servico IS NOT NULL AND TRIM(oi.servico) != ''
        GROUP BY oi.servico, oi.sistema, oi.categoria
        ORDER BY cnt DESC, oi.sistema
        LIMIT 30
    """)
    for servico, sis, cat, cnt in cur.fetchall():
        w(f"  {cnt:3d}x | {cat:12s} | {sis:20s} | {servico}")

    # ── Pendências ────────────────────────────────────────────────────────────
    w("\n── PENDÊNCIAS ────────────────────────────────────────────────────────────────")
    cur.execute("""
        SELECT tipo, status, COUNT(*) cnt
        FROM pendencias_consolidacao
        GROUP BY tipo, status ORDER BY tipo, status
    """)
    for tipo, status, cnt in cur.fetchall():
        icon = "✓" if status == "resolvido" else "⏳"
        w(f"  {icon} {tipo:<35s} {status:<12s} {cnt}")

    cur.execute("SELECT COUNT(*) FROM pendencias_consolidacao WHERE status='pendente'")
    total_pend = cur.fetchone()[0]
    w(f"\n  Total pendências ativas: {total_pend}")

    # ── Integridade ───────────────────────────────────────────────────────────
    w("\n── INTEGRIDADE ──────────────────────────────────────────────────────────────")
    cur.execute("PRAGMA integrity_check")
    ic = cur.fetchone()[0]
    w(f"  integrity_check: {ic}  {'✓' if ic=='ok' else '✗'}")

    cur.execute("PRAGMA foreign_key_check")
    fk_v = cur.fetchall()
    w(f"  foreign_key_check: {len(fk_v)} violações (esperadas: 8 pré-existentes em reembolsos)")

    w("\n" + "=" * 80)
    w("FIM DO RELATÓRIO")
    w("=" * 80)

    output = "\n".join(lines)
    print(output)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output + "\n")
    print(f"\nRelatório salvo: {out_path}")

    con.close()


if __name__ == "__main__":
    main()
