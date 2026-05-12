"""
FASE FINAL — FA Master: Backup + integrity_check + executa A1→A5 + pós-verificação.
"""
import sqlite3, os, sys, io, shutil, subprocess
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")
SCRATCH = os.path.dirname(os.path.abspath(__file__))

SCRIPTS = [
    ("FA1 — Criar tabelas e colunas",       "faseF_A1_criar_tabelas.py"),
    ("FA2 — Migrar reembolsos",             "faseF_A2_migrar_reembolsos.py"),
    ("FA3 — Migrar faturamento",            "faseF_A3_migrar_faturamento.py"),
    ("FA4 — Migrar empresas/contratos",     "faseF_A4_migrar_empresas_contratos.py"),
    ("FA5 — Migrar colunas frota",          "faseF_A5_migrar_frota_colunas.py"),
]


def backup():
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(ROOT, f"locadora_backup_faseF_A_{ts}.db")
    shutil.copy2(DB_PATH, dst)
    size = os.path.getsize(dst)
    print(f"  Backup: {os.path.basename(dst)} ({size:,} bytes)")
    return dst


def snapshot(con):
    cur = con.cursor()
    counts = {}
    for t in ["os_itens", "ordens_servico", "notas_fiscais", "frota",
              "reembolsos", "faturamento_mensal", "empresas", "clientes",
              "contratos", "contrato_veiculo"]:
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
    print("FASE FINAL — FA MASTER")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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

    print("\nTabelas originais — intactas?")
    for t in ["os_itens", "ordens_servico", "notas_fiscais", "frota"]:
        antes  = snap_antes.get(t)
        depois = snap_depois.get(t)
        ok = "✓" if antes == depois else "✗ MUDOU"
        print(f"  {t:<30s} antes={antes}  depois={depois}  {ok}")

    print("\nNovas tabelas populadas:")
    for t in ["reembolsos", "faturamento_mensal", "empresas", "clientes", "contratos", "contrato_veiculo"]:
        antes  = snap_antes.get(t)
        depois = snap_depois.get(t)
        delta  = f"+{depois}" if antes == 0 else f"{antes}→{depois}"
        ok = "✓" if depois and depois > 0 else "⚠ vazio"
        print(f"  {t:<30s} {delta:>12s}  {ok}")

    print("\nColunas frota:")
    cur.execute("SELECT COUNT(*) FROM frota WHERE valor_total IS NOT NULL")
    print(f"  valor_total preenchido:   {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM frota WHERE ano_modelo IS NOT NULL")
    print(f"  ano_modelo preenchido:    {cur.fetchone()[0]}")

    cur.execute("PRAGMA integrity_check")
    ic2 = cur.fetchone()[0]
    print(f"\n  integrity_check final: {ic2}  {'✓' if ic2=='ok' else '✗'}")

    cur.execute("PRAGMA foreign_key_check")
    fk_v = cur.fetchall()
    fk_novas = [v for v in fk_v if v[0] not in ("reembolsos",)]
    if fk_novas:
        print(f"  ✗ NOVAS FK violations: {len(fk_novas)}")
        for v in fk_novas[:10]:
            print(f"    {v}")
    else:
        print(f"  ✓ FK violations: {len(fk_v)} (pré-existentes em reembolsos: esperado)")

    con.close()

    # ── Resultado ─────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    if erros:
        print(f"CONCLUÍDO COM {len(erros)} ERRO(S):")
        for label, rc in erros:
            print(f"  ✗ {label} (código {rc})")
    else:
        print("FASE FINAL — FA CONCLUÍDA COM SUCESSO.")
    print(f"  Backup disponível: {os.path.basename(backup_path)}")
    print(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
