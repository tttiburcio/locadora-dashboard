"""
FASE 3A.1 — Script 3: Match de Fornecedores (DRY-RUN APENAS)
Nenhum UPDATE/INSERT/DELETE é executado.
Gera relatório de fornecedores únicos, aliases, multi-fornecedor, agrupamentos.
Output: scratch/dryrun_fornecedores.txt
"""
import sys, io, sqlite3, os, unicodedata, re
from collections import defaultdict
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "locadora.db")
OUT_PATH = os.path.join(os.path.dirname(__file__), "dryrun_fornecedores.txt")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

lines = []
def w(s=""): lines.append(s)

# ── Normalização ───────────────────────────────────────────────────────────────
def normalize_fornecedor(v):
    if not v or str(v).strip().lower() in ('nan', 'none', 'nat', '-', '', 'null'):
        return None
    v = str(v).strip()
    v = ' '.join(v.split())
    v = unicodedata.normalize('NFC', v)
    return v.upper()

# ── Coletar fornecedores de todas as tabelas ────────────────────────────────────
fontes = {
    "ordens_servico":      ("fornecedor", "numero_os", "total_os"),
    "notas_fiscais":       ("fornecedor", "numero_nf", "valor_total_nf"),
    "manutencao_parcelas": ("fornecedor", "id",        "valor_parcela"),
    "manutencoes":         ("fornecedor", "id",        "total"),
}

# {fornecedor_normalizado: {tabela: count}}
todos = defaultdict(lambda: defaultdict(int))
# mapeamento normalizado → originais
originais_map = defaultdict(set)
# OS com multi-fornecedor
multi_forn = []

for tabela, (col_forn, col_ref, col_val) in fontes.items():
    try:
        cur.execute(f"SELECT {col_forn}, {col_ref}, {col_val} FROM {tabela} WHERE {col_forn} IS NOT NULL AND TRIM({col_forn}) != ''")
        rows = cur.fetchall()
        for forn, ref, val in rows:
            norm = normalize_fornecedor(forn)
            if norm:
                todos[norm][tabela] += 1
                originais_map[norm].add(str(forn).strip())
            if forn and '/' in str(forn):
                multi_forn.append((tabela, ref, forn, val))
    except Exception as e:
        w(f"  AVISO: erro ao ler {tabela}: {e}")

# ── OS com multi-fornecedor (detalhar via ordens_servico) ─────────────────────
cur.execute("""
    SELECT numero_os, fornecedor, total_os
    FROM ordens_servico
    WHERE fornecedor LIKE '%/%' AND deletado_em IS NULL
    ORDER BY fornecedor
""")
os_multi = cur.fetchall()

# ── Detectar possíveis aliases por prefixo/distância simples ──────────────────
norms_list = sorted(todos.keys())

def similar_prefix(a, b, min_len=6):
    a, b = a.upper(), b.upper()
    if a == b:
        return False
    prefix = os.path.commonprefix([a, b])
    return len(prefix) >= min_len and (prefix in a or prefix in b)

alias_grupos = []
visitados = set()
for i, fa in enumerate(norms_list):
    if fa in visitados:
        continue
    grupo = [fa]
    for fb in norms_list[i+1:]:
        if fb in visitados:
            continue
        if similar_prefix(fa, fb):
            grupo.append(fb)
            visitados.add(fb)
    if len(grupo) > 1:
        visitados.add(fa)
        alias_grupos.append(grupo)

# ── Fornecedores NULL por tabela ────────────────────────────────────────────────
nulls = {}
for tabela, (col_forn, col_ref, col_val) in fontes.items():
    try:
        cur.execute(f"SELECT COUNT(*) FROM {tabela} WHERE {col_forn} IS NULL OR TRIM({col_forn}) = ''")
        nulls[tabela] = cur.fetchone()[0]
    except:
        nulls[tabela] = "N/A"

# ── Escrever relatório ─────────────────────────────────────────────────────────
w("=" * 80)
w("FASE 3A.1 — RELATÓRIO DE FORNECEDORES (DRY-RUN)")
w(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
w("NENHUM UPDATE FOI EXECUTADO.")
w("=" * 80)
w()
w(f"Total de fornecedores únicos (normalizados, 4 tabelas): {len(todos)}")
w()

# 1. Fornecedores simples (sem alias detectado, sem "/")
w("-" * 60)
w("--- FORNECEDORES SIMPLES (forma canônica única) ---")
simples = [(f, sum(v.values())) for f, v in todos.items()
           if f not in {g for grp in alias_grupos for g in grp}
           and '/' not in f]
simples.sort(key=lambda x: -x[1])
w(f"  {'fornecedor':<50}  {'total_ocorrencias':>18}")
w("  " + "-" * 70)
for forn, cnt in simples:
    w(f"  {forn:<50}  {cnt:>18}")
w()

# 2. Possíveis aliases
w("-" * 60)
w(f"--- POSSÍVEIS ALIASES (grafias diferentes, mesmo fornecedor) — {len(alias_grupos)} grupos ---")
for grupo in alias_grupos:
    cnts = [(f, sum(todos[f].values())) for f in grupo]
    canonico = max(cnts, key=lambda x: x[1])[0]
    w()
    w(f"  Grupo canônico sugerido: \"{canonico}\"")
    for forn, cnt in sorted(cnts, key=lambda x: -x[1]):
        orig = " | ".join(sorted(originais_map[forn]))
        diff = "(acentuação)" if unicodedata.normalize('NFD', forn.lower()).encode('ascii','ignore') == \
                                  unicodedata.normalize('NFD', canonico.lower()).encode('ascii','ignore') else "(prefixo)"
        marcador = "→ canônico" if forn == canonico else "  alias"
        w(f"    {marcador}: \"{forn}\" ({cnt} ocorrências) {diff}")
        if orig != forn:
            w(f"             forma original: \"{orig}\"")
w()

# 3. Multi-fornecedor
w("-" * 60)
w(f"--- MULTI-FORNECEDOR (contém '/') — {len(os_multi)} OS ---")
w()
for numero_os, forn, total in os_multi:
    candidatos = [c.strip() for c in str(forn).split('/') if c.strip()]
    total_str = f"R$ {float(total):,.2f}" if total else "—"
    w(f"  {numero_os:<16} | {total_str:>14} | \"{forn}\"")
    w(f"    → Candidatos a separar: {candidatos}")
w()

# 4. Fornecedores NULL
w("-" * 60)
w("--- FORNECEDORES NULL / VAZIOS POR TABELA ---")
for tabela, cnt in nulls.items():
    w(f"  {tabela:<30}: {cnt} registros sem fornecedor")
w()

# 5. Resumo
w("=" * 80)
w("RESUMO DE RISCO")
w("=" * 80)
total_forn = len(todos)
total_alias = sum(len(g) for g in alias_grupos)
total_multi = len(os_multi)
total_nulos = sum(v for v in nulls.values() if isinstance(v, int))
w(f"  Fornecedores únicos (normalizados)  : {total_forn}")
w(f"  Em grupos com possível alias        : {total_alias} fornecedores em {len(alias_grupos)} grupos")
w(f"  OS com multi-fornecedor (\"/\")       : {total_multi}")
w(f"  Registros sem fornecedor (4 tabelas): {total_nulos}")
w()
w("AÇÕES NECESSÁRIAS ANTES DE CRIAR TABELA fornecedores:")
w("  1. Revisar grupos de alias — confirmar se são o mesmo fornecedor")
w("  2. Definir nome canônico para cada grupo")
w("  3. Decidir tratamento das OS com '/' — 1 vínculo vs múltiplos vínculos")
w("  4. Obter CNPJ dos principais fornecedores para deduplicação definitiva")
w("  Nenhuma alteração foi feita neste script.")

conn.close()

output = "\n".join(lines)
print(output)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(output)
print(f"\nRelatório salvo em: {OUT_PATH}", file=sys.stderr)
