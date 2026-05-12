"""
FASE 3B — Script 5: Criar pendências iniciais para casos não resolvidos automaticamente.
Idempotente: verifica duplicatas antes de inserir.
"""
import sqlite3, os, sys, io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")


def pendencia_existe(cur, tipo, tabela, registro_id, campo):
    cur.execute(
        """SELECT 1 FROM pendencias_consolidacao
           WHERE tipo=? AND tabela_origem=? AND registro_id=? AND campo=? AND status='pendente'""",
        (tipo, tabela, registro_id, campo),
    )
    return cur.fetchone() is not None


def inserir(cur, tipo, tabela, registro_id, campo, valor_sql, valor_excel, sugestao, nivel, obs=None):
    if pendencia_existe(cur, tipo, tabela, registro_id, campo):
        return False
    cur.execute(
        """INSERT INTO pendencias_consolidacao
           (tipo, tabela_origem, registro_id, campo, valor_sql, valor_excel, sugestao_sistema, nivel_confianca, observacao)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (tipo, tabela, registro_id, campo, valor_sql, valor_excel, sugestao, nivel, obs),
    )
    return True


def main():
    print("=" * 70)
    print("FASE 3B — Script 5: Popular Pendências")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = OFF")
    cur = con.cursor()

    totais: dict[str, int] = {}

    # ── 1. conflito_data: OS-2026-0180 ───────────────────────────────────────
    print("\n[1] conflito_data")
    cur.execute("""
        SELECT id, numero_os, data_execucao
        FROM ordens_servico
        WHERE numero_os = 'OS-2026-0180' AND deletado_em IS NULL
    """)
    row = cur.fetchone()
    n = 0
    if row:
        os_id, numero_os, data_sql = row
        try:
            con.execute("BEGIN")
            ok = inserir(cur, "conflito_data", "ordens_servico", os_id,
                         "data_execucao", str(data_sql), "2026-03-17",
                         None, "CRITICO",
                         "SQL=2026-03-10 vs Excel=2026-03-17 — revisão manual necessária")
            con.commit()
            if ok:
                n = 1
        except Exception as e:
            con.rollback()
            print(f"  ERRO: {e}")
    print(f"  conflito_data criadas: {n}")
    totais["conflito_data"] = n

    # ── 2. fornecedor_multi: OS com '/' ───────────────────────────────────────
    print("\n[2] fornecedor_multi")
    cur.execute("""
        SELECT id, numero_os, fornecedor, total_os
        FROM ordens_servico
        WHERE fornecedor LIKE '%/%' AND deletado_em IS NULL
    """)
    multis = cur.fetchall()
    n = 0
    try:
        con.execute("BEGIN")
        for os_id, numero_os, forn, total in multis:
            candidatos = [p.strip() for p in forn.split("/") if p.strip()]
            sugestao = ", ".join(candidatos)
            ok = inserir(cur, "fornecedor_multi", "ordens_servico", os_id,
                         "fornecedor", forn, None,
                         sugestao, "MEDIA",
                         f"OS {numero_os}: R$ {total or 0:,.2f} — separar em {len(candidatos)} fornecedores")
            if ok:
                n += 1
        con.commit()
    except Exception as e:
        con.rollback()
        print(f"  ERRO: {e}")
    print(f"  fornecedor_multi criadas: {n} (de {len(multis)} OS com '/')")
    totais["fornecedor_multi"] = n

    # ── 3. fornecedor_sem_match: OS simples sem FK preenchida ─────────────────
    print("\n[3] fornecedor_sem_match")
    cur.execute("""
        SELECT id, numero_os, fornecedor
        FROM ordens_servico
        WHERE fornecedor_id IS NULL
          AND fornecedor IS NOT NULL AND TRIM(fornecedor) != ''
          AND fornecedor NOT LIKE '%/%'
          AND deletado_em IS NULL
    """)
    sem_match = cur.fetchall()
    n = 0
    try:
        con.execute("BEGIN")
        for os_id, numero_os, forn in sem_match:
            ok = inserir(cur, "fornecedor_sem_match", "ordens_servico", os_id,
                         "fornecedor", forn, None,
                         None, "BAIXA",
                         f"OS {numero_os}: fornecedor '{forn}' sem match no catálogo")
            if ok:
                n += 1
        con.commit()
    except Exception as e:
        con.rollback()
        print(f"  ERRO: {e}")
    print(f"  fornecedor_sem_match criadas: {n}")
    totais["fornecedor_sem_match"] = n

    # ── 4. servico_sem_grupo: os_itens sem servico_catalogo_id ───────────────
    print("\n[4] servico_sem_grupo")
    cur.execute("""
        SELECT DISTINCT TRIM(servico)
        FROM os_itens
        WHERE servico_catalogo_id IS NULL
          AND servico IS NOT NULL AND TRIM(servico) != ''
        ORDER BY servico
    """)
    servicos_sem = [r[0] for r in cur.fetchall()]

    cur.execute("""
        SELECT oi.id, TRIM(oi.servico), oi.os_id, oi.sistema, oi.categoria
        FROM os_itens oi
        WHERE oi.servico_catalogo_id IS NULL
          AND oi.servico IS NOT NULL AND TRIM(oi.servico) != ''
        ORDER BY oi.servico
    """)
    itens_sem = cur.fetchall()
    n = 0
    try:
        con.execute("BEGIN")
        for item_id, servico, os_id, sistema, categoria in itens_sem:
            ok = inserir(cur, "servico_sem_grupo", "os_itens", item_id,
                         "servico", servico, None,
                         None, "MEDIA",
                         f"sistema={sistema}, categoria={categoria} — sem grupo no catálogo")
            if ok:
                n += 1
        con.commit()
    except Exception as e:
        con.rollback()
        print(f"  ERRO: {e}")
    print(f"  servico_sem_grupo criadas: {n} ({len(servicos_sem)} serviços distintos sem grupo)")
    totais["servico_sem_grupo"] = n

    # ── 5. reembolso_sem_veiculo: reembolsos com id_veiculo=0 ────────────────
    print("\n[5] reembolso_sem_veiculo")
    cur.execute("""
        SELECT id, id_veiculo
        FROM reembolsos
        WHERE id_veiculo = 0 OR id_veiculo IS NULL
    """)
    reimbs = cur.fetchall()
    n = 0
    try:
        con.execute("BEGIN")
        for reimb_id, id_veic in reimbs:
            ok = inserir(cur, "reembolso_sem_veiculo", "reembolsos", reimb_id,
                         "id_veiculo", str(id_veic), None,
                         None, "CRITICO",
                         "id_veiculo=0 — violação de FK pré-existente, requer revisão manual")
            if ok:
                n += 1
        con.commit()
    except Exception as e:
        con.rollback()
        print(f"  ERRO: {e}")
    print(f"  reembolso_sem_veiculo criadas: {n}")
    totais["reembolso_sem_veiculo"] = n

    # ── Resumo ────────────────────────────────────────────────────────────────
    cur.execute("""
        SELECT tipo, COUNT(*), status FROM pendencias_consolidacao
        GROUP BY tipo, status ORDER BY tipo
    """)
    rows = cur.fetchall()

    print("\n" + "=" * 70)
    print("RESUMO DE PENDÊNCIAS:")
    print(f"  {'Tipo':<35s} {'Qtd':>5s}  {'Status'}")
    print(f"  {'-'*35} {'-'*5}  {'-'*10}")
    for tipo, qtd, status in rows:
        print(f"  {tipo:<35s} {qtd:>5d}  {status}")

    cur.execute("SELECT COUNT(*) FROM pendencias_consolidacao WHERE status='pendente'")
    total_pend = cur.fetchone()[0]
    print(f"\n  Total pendente: {total_pend}")

    con.close()
    print("\nScript 5 concluído.")
    print("=" * 70)


if __name__ == "__main__":
    main()
