"""
FASE 3A.1 — Script 1: Inferência de Categoria (DRY-RUN APENAS)
Nenhum UPDATE/INSERT/DELETE é executado.
Gera proposta de inferência com taxa de confiança para os 130 os_itens sem categoria.
Output: scratch/dryrun_categoria.txt
"""
import sys, io, sqlite3, os
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "locadora.db")
OUT_PATH = os.path.join(os.path.dirname(__file__), "dryrun_categoria.txt")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

lines = []

def w(s=""):
    lines.append(s)

# ── Buscar os_itens sem categoria ──────────────────────────────────────────────
cur.execute("""
    SELECT
        oi.id            AS item_id,
        oi.os_id,
        os.numero_os,
        oi.sistema,
        COALESCE(oi.servico, '') AS servico,
        COALESCE(oi.descricao, '') AS descricao,
        COALESCE(oi.manejo_pneu, '') AS manejo_pneu,
        COALESCE(oi.categoria, '') AS categoria_atual,
        -- tipo_nf da(s) NF(s) vinculadas à OS
        (SELECT GROUP_CONCAT(DISTINCT nf.tipo_nf)
         FROM notas_fiscais nf
         WHERE nf.os_id = oi.os_id AND nf.deletado_em IS NULL
        ) AS tipos_nf,
        (SELECT COUNT(DISTINCT nf.id)
         FROM notas_fiscais nf
         WHERE nf.os_id = oi.os_id AND nf.deletado_em IS NULL
        ) AS qtd_nfs
    FROM os_itens oi
    JOIN ordens_servico os ON os.id = oi.os_id
    WHERE (oi.categoria IS NULL OR TRIM(oi.categoria) = '')
      AND os.deletado_em IS NULL
    ORDER BY oi.sistema, oi.servico
""")
rows = [dict(r) for r in cur.fetchall()]

INVALID_CATEGORIA = {'', '-', 'nan', 'none', 'null', 'nat'}

def inferir(row):
    """Retorna (categoria_proposta, confianca_pct, regra, nivel)."""
    sistema   = (row["sistema"] or "").strip()
    servico   = (row["servico"] or "").strip().upper()
    descricao = (row["descricao"] or "").strip().upper()
    manejo    = (row["manejo_pneu"] or "").strip().lower()
    tipos_nf  = row["tipos_nf"] or ""
    qtd_nfs   = row["qtd_nfs"] or 0
    texto     = servico + " " + descricao

    # Regra 1 — tipo_nf único e não misto → confiança >= 90%
    if qtd_nfs == 1:
        if tipos_nf == "Produto":
            return ("Compra",  92, "Regra 1 — tipo_nf=Produto (1 NF)", "ALTA")
        if tipos_nf == "Servico":
            return ("Servico", 92, "Regra 1 — tipo_nf=Servico (1 NF)", "ALTA")
    if qtd_nfs > 1 and "," not in tipos_nf:
        # múltiplas NFs mas todas do mesmo tipo
        if tipos_nf == "Produto":
            return ("Compra",  88, "Regra 1 — tipo_nf=Produto (múlt. NFs)", "ALTA")
        if tipos_nf == "Servico":
            return ("Servico", 88, "Regra 1 — tipo_nf=Servico (múlt. NFs)", "ALTA")

    # Regra 2 — sistema específico com padrão forte
    if sistema.lower() == "revisao":
        return ("Servico", 87, "Regra 2 — sistema=Revisao (100% Serviço no Excel)", "ALTA")
    if sistema.lower() == "pneu" and manejo and manejo != "recapadora":
        return ("Compra",  86, "Regra 2 — sistema=Pneu + manejo preenchido", "ALTA")
    if sistema.lower() == "pneu" and manejo == "recapadora":
        return ("Servico", 85, "Regra 2 — sistema=Pneu + manejo=Recapadora", "ALTA")

    # Regra 3 — palavras-chave no texto do serviço
    palavras_compra  = ["KIT", "FORNEC", "SUBST", "PNEU", "PEÇA", "PECA",
                        "BALDE", "LITRO", "UNID", "MATERIAL", "COMPRA",
                        "AQUISIC", "REPOSIC", "CONJUNTO", "FILTRO"]
    palavras_servico = ["REPARO", "TROCA", "ALINHA", "BALANCE", "REVISAO",
                        "REVISÃO", "M.O.", "MÃO DE OBRA", "MAO DE OBRA",
                        "SERVIÇO", "SERVICO", "LAVAGEM", "DIAGNOSTICO",
                        "DIAGNÓSTICO", "MANUTENCAO", "MANUTENÇÃO", "SOCORRO",
                        "GUINCHO", "MONTAGEM", "DESMONTAGEM", "LIMPEZA",
                        "REGULAGEM", "AJUSTE", "TESTE", "INSPECAO"]

    matches_compra  = [p for p in palavras_compra  if p in texto]
    matches_servico = [p for p in palavras_servico if p in texto]

    if matches_compra and not matches_servico:
        return ("Compra",  72, f"Regra 3 — palavras-chave compra: {matches_compra}", "MEDIA")
    if matches_servico and not matches_compra:
        return ("Servico", 72, f"Regra 3 — palavras-chave serviço: {matches_servico}", "MEDIA")
    if matches_compra and matches_servico:
        return (None, 40, f"Regra 3 — palavras mistas: compra={matches_compra} servico={matches_servico}", "AMBIGUO")

    # Regra 4 — NFs mistas ou sem informação suficiente
    if "," in tipos_nf:
        return (None, 35, f"Regra 4 — NFs com tipos mistos: {tipos_nf}", "AMBIGUO")
    if qtd_nfs == 0:
        return (None, 0, "Regra 5 — OS sem NF vinculada", "IMPOSSIVEL")

    return (None, 20, "Regra 4 — sem padrão identificável", "AMBIGUO")

# ── Classificar todos os itens ──────────────────────────────────────────────────
resultados = {"ALTA": [], "MEDIA": [], "AMBIGUO": [], "IMPOSSIVEL": []}
for row in rows:
    cat, conf, regra, nivel = inferir(row)
    row["categoria_proposta"] = cat
    row["confianca"] = conf
    row["regra"] = regra
    row["nivel"] = nivel
    resultados[nivel].append(row)

# ── Escrever relatório ─────────────────────────────────────────────────────────
w("=" * 80)
w("FASE 3A.1 — PROPOSTA DE INFERÊNCIA DE CATEGORIA (DRY-RUN)")
w(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
w("NENHUM UPDATE FOI EXECUTADO. Este relatório é somente leitura.")
w("=" * 80)
w()
w(f"Total de os_itens sem categoria: {len(rows)}")
w()

for nivel, label in [
    ("ALTA",       "ALTA CONFIANÇA (>= 85%)"),
    ("MEDIA",      "MÉDIA CONFIANÇA (60–84%)"),
    ("AMBIGUO",    "AMBÍGUO / REVISÃO HUMANA (< 60%)"),
    ("IMPOSSIVEL", "IMPOSSÍVEL INFERIR"),
]:
    grupo = resultados[nivel]
    w("-" * 60)
    w(f"--- {label} ---")
    w(f"Subtotal: {len(grupo)} itens")
    w()
    if grupo:
        w(f"{'item_id':>8}  {'numero_os':<16}  {'sistema':<14}  {'servico':<35}  {'tipo_nf':<10}  {'cat_proposta':<10}  {'conf%':>5}  regra")
        w("-" * 140)
        for r in grupo:
            cat_str  = r["categoria_proposta"] or "(nenhuma)"
            servico  = (r["servico"] or "")[:35]
            tipo_nf  = (r["tipos_nf"] or "—")[:10]
            w(f"{r['item_id']:>8}  {r['numero_os']:<16}  {r['sistema']:<14}  {servico:<35}  {tipo_nf:<10}  {cat_str:<10}  {r['confianca']:>5}%  {r['regra']}")
    w()

# ── Resumo ─────────────────────────────────────────────────────────────────────
w("=" * 80)
w("RESUMO")
w("=" * 80)
total = len(rows)
for nivel, label in [("ALTA", "Alta confiança"), ("MEDIA", "Média confiança"),
                     ("AMBIGUO", "Ambíguo"), ("IMPOSSIVEL", "Impossível")]:
    n = len(resultados[nivel])
    pct = n / total * 100 if total else 0
    w(f"  {label:<20}: {n:>4} itens ({pct:.1f}%)")
w()

# ── SQL simulado ───────────────────────────────────────────────────────────────
w("=" * 80)
w("SQL QUE SERIA EXECUTADO — DRY-RUN (NÃO APLICADO)")
w("=" * 80)
w()
w("-- Alta confiança (aplicável automaticamente após aprovação humana):")
for r in resultados["ALTA"]:
    if r["categoria_proposta"]:
        w(f"UPDATE os_itens SET categoria = '{r['categoria_proposta']}' "
          f"WHERE id = {r['item_id']};  -- {r['numero_os']} | {r['sistema']} | conf={r['confianca']}%")
w()
w("-- Média confiança (requer revisão por amostragem):")
for r in resultados["MEDIA"]:
    if r["categoria_proposta"]:
        w(f"-- UPDATE os_itens SET categoria = '{r['categoria_proposta']}' "
          f"WHERE id = {r['item_id']};  -- {r['numero_os']} | {r['sistema']} | conf={r['confianca']}%")
w()
w("-- Ambíguos e impossíveis: NÃO gerar SQL — exigem revisão humana caso a caso.")

conn.close()

output = "\n".join(lines)
print(output)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(output)
print(f"\nRelatório salvo em: {OUT_PATH}", file=sys.stderr)
