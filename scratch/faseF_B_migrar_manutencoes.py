"""
FASE FINAL — FB: Histórico de manutenções Excel → SQL.

Resultado da análise: TODAS as 200 OS do Excel já estão em ordens_servico
(o SQL tem 212 — 12 novas criadas pelo frontend que não existem no Excel).
Portanto: zero linhas a migrar.

Este script:
1. Confirma a cobertura (diagnóstico)
2. Marca origem='excel_legado' nas OS que vieram do Excel
3. Marca origem='frontend' nas OS que existem apenas no SQL
Idempotente (UPDATE WHERE origem IS NULL).
"""
import sqlite3, os, sys, io
import pandas as pd
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")
XL_PATH = os.path.join(ROOT, "Locadora.xlsx")
ABA     = "🔧 MANUTENCOES"


def main():
    print("=" * 70)
    print("FASE FINAL — FB: Histórico Manutenções Excel → SQL")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    df = pd.read_excel(XL_PATH, sheet_name=ABA)
    os_excel = set(df["IDOrdServ"].dropna().unique())
    print(f"Excel: {len(df)} linhas, {len(os_excel)} OS únicas")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("SELECT numero_os FROM ordens_servico WHERE numero_os IS NOT NULL")
    os_sql_all = {r[0] for r in cur.fetchall()}

    so_excel = os_excel - os_sql_all
    so_sql   = os_sql_all - os_excel
    em_ambos = os_excel & os_sql_all

    print(f"SQL:        {len(os_sql_all)} OS com numero_os")
    print(f"Em ambos:   {len(em_ambos)} OS")
    print(f"Só Excel:   {len(so_excel)} OS  (legado a migrar)")
    print(f"Só SQL:     {len(so_sql)} OS  (novas via frontend)")

    if so_excel:
        print(f"\n⚠ ATENÇÃO: {len(so_excel)} OS no Excel não encontradas no SQL:")
        for os_id in sorted(so_excel):
            print(f"  {os_id}")
        print("\nMigração de OS legadas não implementada nesta fase.")
        print("Adicionar manualmente via frontend ou nova fase de migração.")
    else:
        print("\n✓ Cobertura completa — todas as OS do Excel já estão no SQL.")

    # ── Marcar origens ─────────────────────────────────────────────────────────
    print("\n[1] Marcando origem='excel_legado' em OS que vieram do Excel...")
    try:
        con.execute("BEGIN")

        # OS em ambos → excel_legado (foram importadas do Excel na fase 3A)
        placeholders = ",".join("?" * len(em_ambos))
        if em_ambos:
            cur.execute(
                f"""UPDATE ordens_servico
                    SET origem = 'excel_legado'
                    WHERE numero_os IN ({placeholders})
                      AND (origem IS NULL OR origem = '')""",
                list(em_ambos),
            )
            marcadas_legado = cur.rowcount
        else:
            marcadas_legado = 0

        # OS só no SQL → frontend
        if so_sql:
            placeholders2 = ",".join("?" * len(so_sql))
            cur.execute(
                f"""UPDATE ordens_servico
                    SET origem = 'frontend'
                    WHERE numero_os IN ({placeholders2})
                      AND (origem IS NULL OR origem = '')""",
                list(so_sql),
            )
            marcadas_frontend = cur.rowcount
        else:
            marcadas_frontend = 0

        # OS sem numero_os (legado sem ID) → excel_legado_sem_id
        cur.execute(
            """UPDATE ordens_servico
               SET origem = 'excel_legado_sem_id'
               WHERE numero_os IS NULL
                 AND (origem IS NULL OR origem = '')"""
        )
        marcadas_sem_id = cur.rowcount

        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise RuntimeError(f"Erro ao marcar origens: {e}")

    print(f"  Marcadas excel_legado:        {marcadas_legado}")
    print(f"  Marcadas frontend:            {marcadas_frontend}")
    print(f"  Marcadas excel_legado_sem_id: {marcadas_sem_id}")

    # ── Resumo ─────────────────────────────────────────────────────────────────
    print("\nDistribuição de origem:")
    cur.execute("""
        SELECT COALESCE(origem, 'NULL'), COUNT(*)
        FROM ordens_servico
        GROUP BY origem ORDER BY origem
    """)
    for origem, cnt in cur.fetchall():
        print(f"  {origem:<30s} {cnt}")

    cur.execute("SELECT COUNT(*) FROM ordens_servico")
    total = cur.fetchone()[0]
    print(f"\n  Total ordens_servico: {total}  ✓")

    cur.execute("PRAGMA integrity_check")
    print(f"  integrity_check: {cur.fetchone()[0]}")

    con.close()
    print(f"\nFB concluído: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
