"""
FASE FINAL — FA5: Migrar colunas AnoModelo, TabelaFipe, ValorImplemento do Excel → frota SQL.
Idempotente: só atualiza onde a coluna SQL estiver NULL.
"""
import sqlite3, os, sys, io
import pandas as pd
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT    = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB_PATH = os.path.join(ROOT, "locadora.db")
XL_PATH = os.path.join(ROOT, "Locadora.xlsx")
ABA     = "🚛 FROTA"


def safe_float(val):
    if pd.isna(val) or val is None:
        return None
    try:
        f = float(val)
        return None if f == 0.0 else f
    except Exception:
        return None


def safe_year(val):
    if pd.isna(val) or val is None:
        return None
    try:
        f = float(val)
        if f == 0.0:
            return None
        return str(int(f))
    except Exception:
        s = str(val).strip()
        return s if s and s not in ("nan", "none", "0", "0.0") else None


def main():
    print("=" * 70)
    print("FASE FINAL — FA5: Migrar colunas frota (AnoModelo, TabelaFipe, ValorImplemento)")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    df = pd.read_excel(XL_PATH, sheet_name=ABA)
    print(f"Excel: {len(df)} veículos na aba '{ABA}'")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Mapa placa→id no SQL
    cur.execute("SELECT id, placa FROM frota")
    placa_to_id = {row[1].strip().upper(): row[0] for row in cur.fetchall()}

    atualizados = 0
    nao_encontrados = 0

    try:
        con.execute("BEGIN")
        for _, row in df.iterrows():
            placa = str(row.get("Placa", "")).strip().upper()
            if not placa or placa.lower() in ("nan", "none"):
                continue

            id_sql = placa_to_id.get(placa)
            if id_sql is None:
                nao_encontrados += 1
                continue

            ano_modelo      = safe_year(row.get("AnoModelo"))
            tabela_fipe     = safe_float(row.get("TabelaFipe"))
            valor_implemento = safe_float(row.get("ValorImplemento"))
            valor_total     = safe_float(row.get("ValorTotal"))

            # Atualiza apenas campos que estão NULL no SQL
            cur.execute("""
                UPDATE frota SET
                    ano_modelo       = COALESCE(ano_modelo, ?),
                    tabela_fipe      = COALESCE(tabela_fipe, ?),
                    valor_implemento = COALESCE(valor_implemento, ?),
                    valor_total      = COALESCE(valor_total, ?)
                WHERE id = ?
            """, (ano_modelo, tabela_fipe, valor_implemento, valor_total, id_sql))

            if cur.rowcount:
                atualizados += 1

        con.commit()
    except Exception as e:
        con.rollback()
        con.close()
        raise RuntimeError(f"Erro na migração de colunas frota: {e}")

    # Verificação
    cur.execute("SELECT COUNT(*) FROM frota WHERE valor_total IS NOT NULL")
    com_total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM frota WHERE ano_modelo IS NOT NULL")
    com_ano = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM frota")
    total_frota = cur.fetchone()[0]

    print(f"\nResultados:")
    print(f"  Veículos atualizados:     {atualizados}")
    print(f"  Não encontrados no SQL:   {nao_encontrados}")
    print(f"\nCobertura pós-migração:")
    print(f"  valor_total preenchido:   {com_total}/{total_frota}")
    print(f"  ano_modelo preenchido:    {com_ano}/{total_frota}")

    cur.execute("PRAGMA integrity_check")
    print(f"\n  integrity_check: {cur.fetchone()[0]}")

    con.close()
    print(f"\nFA5 concluído: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
