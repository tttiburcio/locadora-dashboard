"""
FASE 3B — Script 6: Relatório de cobertura e estatísticas pós-população.
Somente leitura. Gera scratch/relatorio_fase3b_<timestamp>.txt
"""
import sqlite3, os, sys, io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")
SCRATCH = os.path.dirname(os.path.abspath(__file__))


def fmt(val):
    if val is None:
        return "NULL"
    return str(val)


def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(SCRATCH, f"relatorio_fase3b_{ts}.txt")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    lines = []

    def w(*args):
        lines.append(" ".join(str(a) for a in args))

    w("=" * 80)
    w("RELATÓRIO FASE 3B — COBERTURA E ESTATÍSTICAS")
    w(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    w("=" * 80)

    # ── Contagens originais intactas ──────────────────────────────────────────
    w("\n── CONTAGENS ORIGINAIS ──────────────────────────────────────────────────────")
    for table, expected in [("os_itens", 310), ("ordens_servico", 212), ("notas_fiscais", None), ("frota", None)]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        cnt = cur.fetchone()[0]
        nota = f"  ✓ (esperado {expected})" if expected and cnt == expected else (
               f"  ⚠ ESPERADO {expected}, ENCONTRADO {cnt}" if expected else "")
        w(f"  {table:<30s} {cnt:>6d}{nota}")

    # ── Novas tabelas ─────────────────────────────────────────────────────────
    w("\n── NOVAS TABELAS ────────────────────────────────────────────────────────────")
    new_tables = [
        "fornecedores", "fornecedor_aliases", "catalogo_servicos",
        "catalogo_aliases", "catalogo_componentes", "pneu_medidas",
        "veiculo_pneu_compativel", "catalogo_pneus",
        "pendencias_consolidacao", "consolidacao_log",
    ]
    for t in new_tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            cnt = cur.fetchone()[0]
            w(f"  {t:<35s} {cnt:>6d} registros")
        except Exception as e:
            w(f"  {t:<35s} ERRO: {e}")

    # ── Cobertura FKs novas ───────────────────────────────────────────────────
    w("\n── COBERTURA — ordens_servico.fornecedor_id ─────────────────────────────────")
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE fornecedor_id IS NOT NULL AND deletado_em IS NULL) as com_fk,
            COUNT(*) FILTER (WHERE fornecedor_id IS NULL AND fornecedor IS NOT NULL
                             AND TRIM(fornecedor) != '' AND deletado_em IS NULL) as sem_fk,
            COUNT(*) FILTER (WHERE fornecedor LIKE '%/%' AND deletado_em IS NULL) as multi
        FROM ordens_servico
    """)
    r = cur.fetchone()
    w(f"  Com fornecedor_id preenchido: {r[0]}")
    w(f"  Sem fornecedor_id (sem match): {r[1]}")
    w(f"  Multi-fornecedor (contém '/'): {r[2]}")

    w("\n── COBERTURA — os_itens.servico_catalogo_id ─────────────────────────────────")
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE servico_catalogo_id IS NOT NULL) as com_fk,
            COUNT(*) FILTER (WHERE servico_catalogo_id IS NULL AND servico IS NOT NULL) as sem_fk
        FROM os_itens
    """)
    r = cur.fetchone()
    total_itens = (r[0] or 0) + (r[1] or 0)
    pct = round(100 * r[0] / total_itens, 1) if total_itens else 0
    w(f"  Com servico_catalogo_id: {r[0]} ({pct}%)")
    w(f"  Sem servico_catalogo_id: {r[1]}")

    w("\n── COBERTURA — os_itens.medida_pneu_id ──────────────────────────────────────")
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE medida_pneu_id IS NOT NULL AND sistema='Pneu') as com_fk,
            COUNT(*) FILTER (WHERE medida_pneu_id IS NULL AND sistema='Pneu'
                             AND espec_pneu IS NOT NULL) as sem_fk
        FROM os_itens
    """)
    r = cur.fetchone()
    w(f"  Pneu com medida_pneu_id: {r[0]}")
    w(f"  Pneu sem medida_pneu_id (com espec_pneu): {r[1]}")

    # ── Fornecedores ──────────────────────────────────────────────────────────
    w("\n── TOP 20 FORNECEDORES ──────────────────────────────────────────────────────")
    cur.execute("""
        SELECT f.nome, COUNT(os.id) as cnt
        FROM fornecedores f
        LEFT JOIN ordens_servico os ON os.fornecedor_id = f.id AND os.deletado_em IS NULL
        GROUP BY f.id ORDER BY cnt DESC LIMIT 20
    """)
    for nome, cnt in cur.fetchall():
        w(f"  {nome:<50s} {cnt:>5d} OS")

    # ── Catálogo de serviços ──────────────────────────────────────────────────
    w("\n── CATÁLOGO DE SERVIÇOS — COBERTURA ─────────────────────────────────────────")
    cur.execute("""
        SELECT cs.nome, cs.sistema, cs.categoria, COUNT(oi.id) as cnt
        FROM catalogo_servicos cs
        LEFT JOIN os_itens oi ON oi.servico_catalogo_id = cs.id
        GROUP BY cs.id ORDER BY cnt DESC
    """)
    for nome, sistema, cat, cnt in cur.fetchall():
        w(f"  {nome:<40s} {sistema:<12s} {cat:<10s} {cnt:>5d} itens")

    # ── Pneus ─────────────────────────────────────────────────────────────────
    w("\n── PNEU MEDIDAS ─────────────────────────────────────────────────────────────")
    cur.execute("SELECT medida, id FROM pneu_medidas ORDER BY medida")
    for medida, mid in cur.fetchall():
        cur.execute("SELECT COUNT(*) FROM os_itens WHERE medida_pneu_id=?", (mid,))
        cnt = cur.fetchone()[0]
        w(f"  {medida:<20s} {cnt:>5d} os_itens")

    w("\n── VEICULO_PNEU_COMPATIVEL ──────────────────────────────────────────────────")
    cur.execute("""
        SELECT f.placa, pm.medida, vpc.eixo, vpc.fonte
        FROM veiculo_pneu_compativel vpc
        JOIN frota f ON f.id = vpc.frota_id
        JOIN pneu_medidas pm ON pm.id = vpc.medida_id
        ORDER BY f.placa, pm.medida
    """)
    for placa, medida, eixo, fonte in cur.fetchall():
        w(f"  {placa:<12s} {medida:<20s} eixo={eixo or 'NULL':<12s} fonte={fonte}")

    # ── Pendências ────────────────────────────────────────────────────────────
    w("\n── PENDÊNCIAS POR TIPO ───────────────────────────────────────────────────────")
    cur.execute("""
        SELECT tipo, nivel_confianca, COUNT(*) as cnt, status
        FROM pendencias_consolidacao
        GROUP BY tipo, nivel_confianca, status
        ORDER BY tipo
    """)
    for tipo, nivel, cnt, status in cur.fetchall():
        w(f"  {tipo:<35s} {nivel:<8s} {cnt:>5d}  {status}")

    w("\n── VERIFICAÇÕES DE INTEGRIDADE ──────────────────────────────────────────────")
    cur.execute("PRAGMA integrity_check")
    ic = cur.fetchone()[0]
    w(f"  integrity_check: {ic}")

    cur.execute("PRAGMA foreign_key_check")
    fk_violations = cur.fetchall()
    if fk_violations:
        w(f"  foreign_key_check: {len(fk_violations)} violações (pré-existentes esperadas: 8 em reembolsos)")
        for v in fk_violations:
            w(f"    {v}")
    else:
        w("  foreign_key_check: OK (sem violações)")

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
