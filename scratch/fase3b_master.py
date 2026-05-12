"""
FASE 3B — Script Master: Backup + executa scripts 1-6 em sequência + pós-verificação.
"""
import sqlite3, os, sys, io, shutil, subprocess
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")
SCRATCH = os.path.dirname(os.path.abspath(__file__))

SCRIPTS = [
    ("Script 1 — Criar Estrutura",        "fase3b_criar_estrutura.py"),
    ("Script 2 — Popular Fornecedores",   "fase3b_popular_fornecedores.py"),
    ("Script 3 — Popular Serviços",       "fase3b_popular_servicos.py"),
    ("Script 4 — Popular Pneus",          "fase3b_popular_pneus.py"),
    ("Script 5 — Popular Pendências",     "fase3b_popular_pendencias.py"),
    ("Script 6 — Relatório",              "fase3b_relatorio.py"),
]


def backup():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(ROOT, f"locadora_backup_3b_{ts}.db")
    shutil.copy2(DB_PATH, dst)
    size = os.path.getsize(dst)
    print(f"  Backup: {os.path.basename(dst)} ({size:,} bytes)")
    return dst


def snapshot(con):
    cur = con.cursor()
    counts = {}
    for t in ["os_itens", "ordens_servico", "notas_fiscais", "frota", "manutencao_parcelas"]:
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
    print("FASE 3B — EXECUÇÃO MASTER")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("PROTOCOLO: backup → estrutura → dados → pendências → relatório")
    print("=" * 70)

    if not os.path.exists(DB_PATH):
        print(f"ERRO: DB não encontrado em {DB_PATH}")
        sys.exit(1)

    # ── Backup ────────────────────────────────────────────────────────────────
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
    for t, antes in snap_antes.items():
        depois = snap_depois.get(t)
        ok = "✓" if antes == depois else "✗ MUDOU"
        print(f"  {t:<30s} antes={antes}  depois={depois}  {ok}")

    print("\nNovas tabelas:")
    new_tables = [
        "fornecedores", "fornecedor_aliases", "catalogo_servicos",
        "catalogo_aliases", "pneu_medidas", "veiculo_pneu_compativel",
        "catalogo_pneus", "pendencias_consolidacao", "consolidacao_log",
    ]
    for t in new_tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            cnt = cur.fetchone()[0]
            print(f"  {t:<35s} {cnt:>6d} registros")
        except Exception as e:
            print(f"  {t:<35s} ERRO: {e}")

    print("\nVerificações críticas:")

    cur.execute("SELECT COUNT(*) FROM os_itens WHERE sistema='Pneu' AND LOWER(categoria)='compra' AND espec_pneu IS NOT NULL AND medida_pneu_id IS NULL")
    v1 = cur.fetchone()[0]
    print(f"  pneu+compra sem medida_pneu_id: {v1}  {'✓' if v1==0 else '⚠'}")

    cur.execute("SELECT COUNT(*) FROM ordens_servico WHERE fornecedor_id IS NOT NULL AND deletado_em IS NULL")
    v2 = cur.fetchone()[0]
    print(f"  ordens_servico com fornecedor_id preenchido: {v2}")

    cur.execute("SELECT COUNT(*) FROM pendencias_consolidacao WHERE status='pendente'")
    v3 = cur.fetchone()[0]
    print(f"  pendencias_consolidacao pendentes: {v3}")

    cur.execute("SELECT tipo, COUNT(*) FROM pendencias_consolidacao GROUP BY tipo ORDER BY tipo")
    print("  Pendências por tipo:")
    for tipo, cnt in cur.fetchall():
        print(f"    {tipo:<35s} {cnt}")

    cur.execute("PRAGMA integrity_check")
    ic2 = cur.fetchone()[0]
    print(f"\n  integrity_check final: {ic2}  {'✓' if ic2=='ok' else '✗'}")

    con.close()

    # ── Resultado ─────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    if erros:
        print(f"CONCLUÍDO COM {len(erros)} ERRO(S):")
        for label, rc in erros:
            print(f"  ✗ {label} (código {rc})")
    else:
        print("FASE 3B CONCLUÍDA COM SUCESSO.")
    print(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
