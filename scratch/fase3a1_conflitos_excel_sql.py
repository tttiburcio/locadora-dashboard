"""
FASE 3A.1 — Script 5: Conflitos SQL vs Excel (DRY-RUN APENAS)
Nenhum UPDATE/INSERT/DELETE é executado.
Detecta e classifica conflitos entre Excel MANUTENCOES e ordens_servico SQL.
Output: scratch/dryrun_conflitos.txt
"""
import sys, io, sqlite3, os, unicodedata
import pandas as pd
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB_PATH    = os.path.join(os.path.dirname(__file__), "..", "locadora.db")
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "..", "Locadora.xlsx")
OUT_PATH   = os.path.join(os.path.dirname(__file__), "dryrun_conflitos.txt")

lines = []
def w(s=""): lines.append(s)

# ── Funções de normalização (reutilizadas dos scripts 2 e 3) ───────────────────
def normalize_text(v):
    if not v or str(v).strip().lower() in ('nan', 'none', 'nat', '-', '', 'null'):
        return None
    v = str(v).strip()
    v = ' '.join(v.split())
    v = unicodedata.normalize('NFC', v)
    return v

def normalize_fornecedor(v):
    v = normalize_text(v)
    return v.upper() if v else None

INVALID_VALS = {None, '', '-', 'nan', 'none', 'nat', 'null'}

def is_invalid(v):
    return v is None or str(v).strip().lower() in INVALID_VALS

def parse_date(v):
    if is_invalid(v):
        return None
    try:
        return pd.to_datetime(str(v)).date()
    except:
        return None

def parse_float(v):
    if is_invalid(v):
        return None
    try:
        f = float(str(v).replace(',', '.').replace(' ', ''))
        return round(f, 2)
    except:
        return None

# ── Carregar SQL ───────────────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
    SELECT os.numero_os, os.placa, os.fornecedor, os.total_os,
           os.data_execucao, os.data_entrada, os.status_os,
           GROUP_CONCAT(DISTINCT oi.sistema) as sistemas,
           GROUP_CONCAT(DISTINCT oi.categoria) as categorias
    FROM ordens_servico os
    LEFT JOIN os_itens oi ON oi.os_id = os.id
    WHERE os.deletado_em IS NULL
    GROUP BY os.id
""")
sql_rows = {r["numero_os"]: dict(r) for r in cur.fetchall()}

# ── Carregar Excel ─────────────────────────────────────────────────────────────
df = pd.read_excel(EXCEL_PATH, sheet_name="🔧 MANUTENCOES")

# Normalizar nomes de colunas
df.columns = [c.strip() for c in df.columns]

# Selecionar colunas relevantes
COL_MAP = {
    "IDOrdServ":     "id_ord_serv",
    "Placa":         "placa",
    "Fornecedor":    "fornecedor",
    "TotalOS":       "total_os",
    "DataExecução":  "data_execucao",
    "Categoria":     "categoria",
    "Sistema":       "sistema",
}
# Tentar variações de nome
for col_orig, col_new in list(COL_MAP.items()):
    if col_orig not in df.columns:
        for c in df.columns:
            if col_new.replace("_", "").lower() in c.lower().replace(" ", ""):
                COL_MAP[c] = col_new
                del COL_MAP[col_orig]
                break

df_clean = pd.DataFrame()
for col_excel, col_norm in COL_MAP.items():
    if col_excel in df.columns:
        df_clean[col_norm] = df[col_excel]

# Filtrar linhas com IDOrdServ válido
mask = df_clean["id_ord_serv"].notna() & df_clean["id_ord_serv"].astype(str).str.startswith("OS-")
df_match = df_clean[mask].copy()

# Deduplicar por IDOrdServ (Excel tem múltiplas linhas por OS)
df_dedup = df_match.drop_duplicates(subset=["id_ord_serv"])

# ── Comparar campo a campo ─────────────────────────────────────────────────────
conflitos_criticos  = []
conflitos_moderados = []
estado_b            = []
sem_conflito        = []

for _, ex_row in df_dedup.iterrows():
    nos = str(ex_row.get("id_ord_serv", "")).strip()
    if nos not in sql_rows:
        continue

    sql = sql_rows[nos]
    conflitos_os = []

    # total_os — crítico se divergência > R$1,00
    ex_total  = parse_float(ex_row.get("total_os"))
    sql_total = parse_float(sql.get("total_os"))
    if ex_total is not None and sql_total is not None:
        diff = abs(ex_total - sql_total)
        if diff > 1.0:
            conflitos_os.append(("total_os", "CRITICO",
                                 f"SQL=R${sql_total:,.2f}", f"Excel=R${ex_total:,.2f}",
                                 f"Δ=R${diff:,.2f}"))
    elif is_invalid(sql_total) and ex_total is not None:
        estado_b.append((nos, "total_os", "(NULL)", f"R${ex_total:,.2f}"))

    # data_execucao — crítico se diferente
    ex_data  = parse_date(ex_row.get("data_execucao"))
    sql_data = parse_date(sql.get("data_execucao") or sql.get("data_entrada"))
    if ex_data and sql_data:
        if ex_data != sql_data:
            conflitos_os.append(("data_execucao", "CRITICO",
                                 f"SQL={sql_data}", f"Excel={ex_data}", "→ REVISÃO HUMANA"))
    elif is_invalid(sql.get("data_execucao")) and ex_data:
        estado_b.append((nos, "data_execucao", "(NULL)", str(ex_data)))

    # fornecedor — moderado
    ex_forn  = normalize_fornecedor(ex_row.get("fornecedor"))
    sql_forn = normalize_fornecedor(sql.get("fornecedor"))
    if ex_forn and sql_forn:
        # Se SQL tem "/" pode ser multi-fornecedor — não é conflito
        if ex_forn != sql_forn and '/' not in (sql.get("fornecedor") or ""):
            conflitos_os.append(("fornecedor", "MODERADO",
                                 f'SQL="{sql_forn}"', f'Excel="{ex_forn}"', ""))
    elif is_invalid(sql.get("fornecedor")) and ex_forn:
        estado_b.append((nos, "fornecedor", "(NULL)", ex_forn))

    # placa — crítico se diferente
    ex_placa  = normalize_text(ex_row.get("placa"))
    sql_placa = normalize_text(sql.get("placa"))
    if ex_placa and sql_placa and ex_placa.upper() != sql_placa.upper():
        conflitos_os.append(("placa", "CRITICO",
                             f"SQL={sql_placa}", f"Excel={ex_placa}", "→ REVISÃO HUMANA"))

    # categoria — estado B (SQL quase sempre NULL)
    ex_cat  = normalize_text(ex_row.get("categoria"))
    sql_cat = normalize_text(sql.get("categorias"))
    if is_invalid(sql_cat) and ex_cat:
        estado_b.append((nos, "categoria", "(NULL)", ex_cat))
    elif ex_cat and sql_cat and ex_cat.lower() != sql_cat.lower():
        conflitos_os.append(("categoria", "MODERADO",
                             f'SQL="{sql_cat}"', f'Excel="{ex_cat}"', ""))

    if not conflitos_os:
        sem_conflito.append(nos)
    else:
        for campo, classe, sql_val, ex_val, nota in conflitos_os:
            entry = (nos, campo, sql_val, ex_val, nota)
            if classe == "CRITICO":
                conflitos_criticos.append(entry)
            else:
                conflitos_moderados.append(entry)

# ── Escrever relatório ─────────────────────────────────────────────────────────
w("=" * 80)
w("FASE 3A.1 — RELATÓRIO DE CONFLITOS SQL vs EXCEL (DRY-RUN)")
w(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
w("NENHUM UPDATE FOI EXECUTADO.")
w("=" * 80)
w()
w(f"OS com match Excel ↔ SQL analisadas: {len(df_dedup)}")
w()

# Críticos
w("-" * 60)
w(f"--- CONFLITOS CRÍTICOS — {len(conflitos_criticos)} ---")
w()
if conflitos_criticos:
    for nos, campo, sql_val, ex_val, nota in conflitos_criticos:
        w(f"  {nos:<16} | campo: {campo:<15} | {sql_val:<30} | {ex_val:<30} | {nota}")
else:
    w("  (Nenhum conflito crítico encontrado)")
w()

# Moderados
w("-" * 60)
w(f"--- CONFLITOS MODERADOS — {len(conflitos_moderados)} ---")
w()
if conflitos_moderados:
    for nos, campo, sql_val, ex_val, nota in conflitos_moderados[:40]:
        w(f"  {nos:<16} | campo: {campo:<15} | {sql_val:<40} | {ex_val:<40}")
    if len(conflitos_moderados) > 40:
        w(f"  ... e mais {len(conflitos_moderados) - 40} conflitos moderados")
else:
    w("  (Nenhum conflito moderado encontrado)")
w()

# Estado B
w("-" * 60)
w(f"--- ESTADO B (SQL NULL, Excel tem valor) — {len(estado_b)} casos ---")
w()
if estado_b:
    for nos, campo, sql_val, ex_val in estado_b[:40]:
        w(f"  {nos:<16} | campo: {campo:<15} | SQL={sql_val:<15} | Excel={ex_val}")
    if len(estado_b) > 40:
        w(f"  ... e mais {len(estado_b) - 40} casos Estado B")
else:
    w("  (Nenhum caso Estado B encontrado)")
w()

# Sem conflito
w("-" * 60)
w(f"--- SEM CONFLITO — {len(sem_conflito)} OS ---")
w()

# Risco financeiro
w("=" * 80)
w("RESUMO DE RISCO FINANCEIRO")
w("=" * 80)
total_delta = 0.0
for nos, campo, sql_val, ex_val, nota in conflitos_criticos:
    if campo == "total_os" and "Δ=" in nota:
        try:
            delta_str = nota.replace("Δ=R$", "").replace(".", "").replace(",", ".")
            total_delta += float(delta_str)
        except:
            pass
w(f"  Conflitos críticos:             {len(conflitos_criticos)}")
w(f"  Conflitos moderados:            {len(conflitos_moderados)}")
w(f"  Casos Estado B (SQL NULL):      {len(estado_b)}")
w(f"  OS sem conflito:                {len(sem_conflito)}")
w(f"  Soma divergências financeiras:  R$ {total_delta:,.2f}")
w()
w("AÇÕES NECESSÁRIAS ANTES DA FASE 3A.2:")
w("  1. Revisar e resolver TODOS os conflitos críticos manualmente")
w("  2. Aprovar lista de Estado B para atualização SQL ← dados do Excel")
w("  3. Decidir sobre conflitos moderados de fornecedor caso a caso")
w("  Nenhuma alteração foi feita neste script.")

conn.close()

output = "\n".join(lines)
print(output)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(output)
print(f"\nRelatório salvo em: {OUT_PATH}", file=sys.stderr)
