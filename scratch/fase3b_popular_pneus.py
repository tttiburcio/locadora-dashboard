"""
FASE 3B — Script 4: Popular pneu_medidas, veiculo_pneu_compativel, catalogo_pneus.
Vincula os_itens.medida_pneu_id. Idempotente.
"""
import sqlite3, os, sys, io
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")


def main():
    print("=" * 70)
    print("FASE 3B — Script 4: Popular Pneus")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = OFF")
    cur = con.cursor()

    # ── pneu_medidas ──────────────────────────────────────────────────────────
    print("\n[1/4] pneu_medidas")
    cur.execute("""
        SELECT DISTINCT TRIM(espec_pneu)
        FROM os_itens
        WHERE espec_pneu IS NOT NULL AND TRIM(espec_pneu) != ''
          AND sistema = 'Pneu'
    """)
    medidas_raw = [r[0] for r in cur.fetchall()]
    print(f"  Medidas únicas encontradas: {len(medidas_raw)}")
    for m in medidas_raw:
        print(f"    {m}")

    inseridas_med = 0
    try:
        con.execute("BEGIN")
        for medida in medidas_raw:
            cur.execute(
                "INSERT OR IGNORE INTO pneu_medidas (medida) VALUES (?)",
                (medida,)
            )
            if cur.rowcount:
                inseridas_med += 1
        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise RuntimeError(f"Erro ao inserir pneu_medidas: {e}")

    print(f"  pneu_medidas inseridas: {inseridas_med}")

    # Monta lookup medida → id
    cur.execute("SELECT id, medida FROM pneu_medidas")
    medida_id: dict[str, int] = {r[1]: r[0] for r in cur.fetchall()}

    # ── veiculo_pneu_compativel ───────────────────────────────────────────────
    print("\n[2/4] veiculo_pneu_compativel")
    cur.execute("""
        SELECT DISTINCT os.placa, oi.espec_pneu
        FROM os_itens oi
        JOIN ordens_servico os ON os.id = oi.os_id
        WHERE oi.sistema = 'Pneu'
          AND LOWER(oi.categoria) = 'compra'
          AND oi.espec_pneu IS NOT NULL AND TRIM(oi.espec_pneu) != ''
          AND os.placa IS NOT NULL AND TRIM(os.placa) != ''
          AND os.deletado_em IS NULL
    """)
    pares = cur.fetchall()
    print(f"  Pares placa × medida históricos: {len(pares)}")

    inseridas_vpc = 0
    erros_vpc = 0
    try:
        con.execute("BEGIN")
        for placa, espec in pares:
            placa = placa.strip()
            espec = espec.strip()

            cur.execute("SELECT id FROM frota WHERE TRIM(placa) = ?", (placa,))
            frota_row = cur.fetchone()
            if not frota_row:
                erros_vpc += 1
                continue

            mid = medida_id.get(espec)
            if not mid:
                erros_vpc += 1
                continue

            cur.execute(
                "INSERT OR IGNORE INTO veiculo_pneu_compativel (frota_id, medida_id, fonte) VALUES (?, ?, 'historico')",
                (frota_row[0], mid)
            )
            if cur.rowcount:
                inseridas_vpc += 1
        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise RuntimeError(f"Erro ao inserir veiculo_pneu_compativel: {e}")

    print(f"  veiculo_pneu_compativel inseridos: {inseridas_vpc}")
    if erros_vpc:
        print(f"  Pares sem match (frota ou medida não encontrada): {erros_vpc}")

    # ── catalogo_pneus ────────────────────────────────────────────────────────
    print("\n[3/4] catalogo_pneus")
    cur.execute("""
        SELECT DISTINCT
            TRIM(oi.marca_pneu),
            TRIM(COALESCE(oi.modelo_pneu, '')),
            TRIM(oi.espec_pneu)
        FROM os_itens oi
        WHERE oi.marca_pneu IS NOT NULL AND TRIM(oi.marca_pneu) != ''
          AND oi.espec_pneu IS NOT NULL AND TRIM(oi.espec_pneu) != ''
          AND oi.sistema = 'Pneu'
    """)
    combos = cur.fetchall()
    print(f"  Combinações marca × medida: {len(combos)}")

    inseridas_cat = 0
    try:
        con.execute("BEGIN")
        for marca, modelo, espec in combos:
            mid = medida_id.get(espec)
            modelo_val = modelo if modelo else None
            cur.execute(
                "INSERT OR IGNORE INTO catalogo_pneus (marca, modelo, medida_id) VALUES (?, ?, ?)",
                (marca, modelo_val, mid)
            )
            if cur.rowcount:
                inseridas_cat += 1
                print(f"    {marca:35s} + {espec}")
        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise RuntimeError(f"Erro ao inserir catalogo_pneus: {e}")

    print(f"  catalogo_pneus inseridos: {inseridas_cat}")

    # ── os_itens.medida_pneu_id ───────────────────────────────────────────────
    print("\n[4/4] Vinculando os_itens.medida_pneu_id")
    cur.execute("""
        SELECT id, TRIM(espec_pneu)
        FROM os_itens
        WHERE espec_pneu IS NOT NULL AND TRIM(espec_pneu) != ''
          AND medida_pneu_id IS NULL
          AND sistema = 'Pneu'
    """)
    rows = cur.fetchall()

    vinculados = 0
    sem_match  = 0
    try:
        con.execute("BEGIN")
        for item_id, espec in rows:
            mid = medida_id.get(espec)
            if mid:
                cur.execute(
                    "UPDATE os_itens SET medida_pneu_id = ? WHERE id = ? AND medida_pneu_id IS NULL",
                    (mid, item_id)
                )
                if cur.rowcount:
                    vinculados += 1
            else:
                sem_match += 1
        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise RuntimeError(f"Erro ao vincular medida_pneu_id: {e}")

    print(f"  Vinculados: {vinculados}")
    if sem_match:
        print(f"  Sem match:  {sem_match}")

    # Verificação: pneu+compra com espec_pneu não pode ter medida_pneu_id NULL
    cur.execute("""
        SELECT COUNT(*) FROM os_itens
        WHERE sistema = 'Pneu' AND LOWER(categoria) = 'compra'
          AND espec_pneu IS NOT NULL AND medida_pneu_id IS NULL
    """)
    violacoes = cur.fetchone()[0]
    if violacoes:
        print(f"  AVISO: {violacoes} pneu+compra ainda sem medida_pneu_id")
    else:
        print("  OK: todos pneu+compra com espec_pneu têm medida_pneu_id.")

    con.close()
    print("\nScript 4 concluído.")
    print("=" * 70)


if __name__ == "__main__":
    main()
