"""
FASE 3B.1 — Script Master: Backup + integridade + executa scripts 1-3 + pós-verificação.
"""
import sqlite3, os, sys, io, shutil, subprocess
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")
SCRATCH = os.path.dirname(os.path.abspath(__file__))

SCRIPTS = [
    ("Script 1 — Expandir Catálogo",      "fase3b1_expandir_catalogo.py"),
    ("Script 2 — Atualizar Pendências",   "fase3b1_atualizar_pendencias.py"),
    ("Script 3 — Relatório",              "fase3b1_relatorio.py"),
]


def backup():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(ROOT, f"locadora_backup_3b1_{ts}.db")
    shutil.copy2(DB_PATH, dst)
    size = os.path.getsize(dst)
    print(f"  Backup: {os.path.basename(dst)} ({size:,} bytes)")
    return dst


def snapshot(con):
    cur = con.cursor()
    counts = {}
    for t in ["os_itens", "ordens_servico", "notas_fiscais", "frota",
              "catalogo_servicos", "catalogo_aliases", "pendencias_consolidacao"]:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            counts[t] = cur.fetchone()[0]
        except Exception:
            counts[t] = None
    return counts


def run_script(label, script_name):
    script_path = os.path.join(SCRATCH, script_name)
    print(f"\n{'─'*70}")
    print(f"Executando: {label}")
    print(f"{'─'*70}")
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=SCRATCH,
    )
    return result.returncode


def main():
    print("=" * 70)
    print("FASE 3B.1 — EXECUÇÃO MASTER")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("PROTOCOLO: backup → expandir catálogo → atualizar pendências → relatório")
    print("=" * 70)

    if not os.path.exists(DB_PATH):
        print(f"ERRO: DB não encontrado em {DB_PATH}")
        sys.exit(1)

    # ── Pré-verificação ───────────────────────────────────────────────────────
    print("\n[PRÉ] Backup + verificações iniciais")
    backup_path = backup()

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("PRAGMA integrity_check")
    ic = cur.fetchone()[0]
    print(f"  integrity_check: {ic}")
    if ic != "ok":
        con.close()
        print("ABORTANDO — integrity_check falhou.")
        sys.exit(1)

    snap_antes = snapshot(con)
    print("  Contagens iniciais:")
    for t, c in snap_antes.items():
        print(f"    {t}: {c}")

    # Verificar que temos 59 como baseline
    cur.execute("SELECT COUNT(*) FROM os_itens WHERE servico_catalogo_id IS NOT NULL")
    cobertura_inicial = cur.fetchone()[0]
    print(f"  Cobertura FK inicial: {cobertura_inicial}/310")
    con.close()

    # ── Scripts ───────────────────────────────────────────────────────────────
    erros = []
    for label, script in SCRIPTS:
        rc = run_script(label, script)
        if rc != 0:
            erros.append((label, rc))
            print(f"\nERRO em '{label}' (código {rc}). Abortando sequência.")
            break

    # ── Pós-verificação ───────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("PÓS-VERIFICAÇÃO")
    print(f"{'='*70}")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    snap_depois = snapshot(con)

    print("\nContagens originais — intactas?")
    for t in ["os_itens", "ordens_servico", "notas_fiscais", "frota"]:
        antes = snap_antes.get(t)
        depois = snap_depois.get(t)
        ok = "✓" if antes == depois else "✗ MUDOU"
        print(f"  {t:<30s} antes={antes}  depois={depois}  {ok}")

    print("\nExpansão do catálogo:")
    for t in ["catalogo_servicos", "catalogo_aliases", "pendencias_consolidacao"]:
        antes = snap_antes.get(t)
        depois = snap_depois.get(t)
        delta = f"+{depois-antes}" if depois > antes else str(depois-antes)
        print(f"  {t:<35s} {antes} → {depois} ({delta})")

    print("\nVerificações críticas:")

    cur.execute("SELECT COUNT(*) FROM os_itens WHERE servico_catalogo_id IS NOT NULL")
    cobertura_final = cur.fetchone()[0]
    ganho = cobertura_final - cobertura_inicial
    pct = round(100 * cobertura_final / 310)
    print(f"  Cobertura servico_catalogo_id: {cobertura_inicial} → {cobertura_final} (+{ganho}) = {pct}%")
    ok_cov = "✓" if cobertura_final >= 140 else "⚠ abaixo do esperado (>=140)"
    print(f"  Meta (>=140): {ok_cov}")

    cur.execute("SELECT COUNT(*) FROM catalogo_servicos")
    n_grupos = cur.fetchone()[0]
    print(f"  Grupos canônicos: {n_grupos} (esperado: 18)")
    ok_g = "✓" if n_grupos == 18 else f"⚠ esperado 18"
    print(f"  {ok_g}")

    cur.execute("SELECT COUNT(*) FROM pendencias_consolidacao WHERE tipo='servico_sem_grupo' AND status='pendente'")
    pend_restantes = cur.fetchone()[0]
    print(f"  servico_sem_grupo pendentes: {pend_restantes} (esperado: <100)")
    ok_p = "✓" if pend_restantes < 100 else "⚠ acima do esperado"
    print(f"  {ok_p}")

    cur.execute("PRAGMA integrity_check")
    ic2 = cur.fetchone()[0]
    print(f"\n  integrity_check final: {ic2}  {'✓' if ic2=='ok' else '✗'}")

    cur.execute("PRAGMA foreign_key_check")
    fk_v = cur.fetchall()
    fk_novas = [v for v in fk_v if v[0] != 'reembolsos']
    if fk_novas:
        print(f"  ✗ NOVAS FK violations: {len(fk_novas)}")
        for v in fk_novas:
            print(f"    {v}")
    else:
        print(f"  ✓ Nenhuma nova FK violation (8 pré-existentes em reembolsos: esperado)")

    con.close()

    # ── Resultado ─────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    if erros:
        print(f"CONCLUÍDO COM {len(erros)} ERRO(S):")
        for label, rc in erros:
            print(f"  ✗ {label} (código {rc})")
    else:
        print("FASE 3B.1 CONCLUÍDA COM SUCESSO.")
    print(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
