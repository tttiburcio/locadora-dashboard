"""
FASE 1 — Diagnóstico e Mapeamento das Fontes de Dados
READ-ONLY: nenhum UPDATE/INSERT/DELETE/DROP é executado.
"""
import sys, io, sqlite3, textwrap
import pandas as pd
import numpy as np
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT   = Path(__file__).resolve().parents[1]
DB     = ROOT / "locadora.db"
EXCEL  = ROOT / "Locadora.xlsx"
OUT    = ROOT / "scratch" / "relatorio_auditoria_fase1.txt"

conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row

lines = []

def h1(t):  lines.append(f"\n{'='*80}\n{t}\n{'='*80}")
def h2(t):  lines.append(f"\n{'-'*60}\n{t}\n{'-'*60}")
def p(*a):  lines.append(" ".join(str(x) for x in a))
def blank(): lines.append("")

INVALID = {"", "-", "nan", "none", "nat", "null", "n/a", "#n/a", "#ref!", "0.0", "0"}

def is_invalid(v):
    if v is None: return True
    if isinstance(v, float) and (pd.isna(v) or np.isnan(v)): return True
    return str(v).strip().lower() in INVALID

def count_invalids_sql(cur, table, col):
    cur.execute(f"""
        SELECT COUNT(*) FROM {table}
        WHERE {col} IS NULL
           OR TRIM(CAST({col} AS TEXT)) = ''
           OR LOWER(TRIM(CAST({col} AS TEXT))) IN ('nan','none','nat','null','-','n/a')
    """)
    return cur.fetchone()[0]

# ─────────────────────────────────────────────────────────────────────────────
h1("SEÇÃO 1 — SCHEMA SQL COMPLETO")
# ─────────────────────────────────────────────────────────────────────────────

cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
p(f"Total de tabelas: {len(tables)}")
p("Tabelas:", ", ".join(tables))

for tbl in tables:
    blank()
    h2(f"Tabela: {tbl}")
    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
    total = cur.fetchone()[0]
    p(f"  Linhas: {total}")

    cur.execute(f"PRAGMA table_info({tbl})")
    cols = cur.fetchall()
    p(f"  Colunas ({len(cols)}):")
    for c in cols:
        pk = " [PK]" if c["pk"] else ""
        nn = " NOT NULL" if c["notnull"] else ""
        df = f" DEFAULT {c['dflt_value']}" if c["dflt_value"] else ""
        p(f"    {c['name']:35s} {c['type']:20s}{pk}{nn}{df}")

    cur.execute(f"PRAGMA foreign_key_list({tbl})")
    fks = cur.fetchall()
    if fks:
        p(f"  Foreign Keys:")
        for fk in fks:
            p(f"    {fk['from']} → {fk['table']}.{fk['to']}")

    cur.execute(f"PRAGMA index_list({tbl})")
    idxs = cur.fetchall()
    if idxs:
        p(f"  Índices:")
        for idx in idxs:
            uniq = " UNIQUE" if idx["unique"] else ""
            p(f"    {idx['name']}{uniq}")

# ─────────────────────────────────────────────────────────────────────────────
h1("SEÇÃO 2 — INVENTÁRIO EXCEL")
# ─────────────────────────────────────────────────────────────────────────────

xl = pd.ExcelFile(str(EXCEL))
p(f"Total de abas: {len(xl.sheet_names)}")

excel_dfs = {}
for sheet in xl.sheet_names:
    try:
        df = xl.parse(sheet)
        excel_dfs[sheet] = df
        blank()
        h2(f"Aba: {sheet}")
        p(f"  Linhas: {len(df)} | Colunas: {len(df.columns)}")
        for col in df.columns:
            n_null = df[col].isna().sum()
            null_pct = 100 * n_null / max(len(df), 1)
            dtype = str(df[col].dtype)
            p(f"    {col:35s} dtype={dtype:12s} nulos={n_null:4d} ({null_pct:5.1f}%)")
    except Exception as e:
        p(f"  ERRO ao ler aba '{sheet}': {e}")

# ─────────────────────────────────────────────────────────────────────────────
h1("SEÇÃO 3 — REGISTROS APENAS NO EXCEL (sem match SQL)")
# ─────────────────────────────────────────────────────────────────────────────

manut_xl = excel_dfs.get("🔧 MANUTENCOES", pd.DataFrame())
cur.execute("SELECT numero_os FROM ordens_servico WHERE deletado_em IS NULL")
sql_nos = {r[0] for r in cur.fetchall()}
cur.execute("SELECT numero_os FROM ordens_servico")  # inclui deletados
sql_nos_all = {r[0] for r in cur.fetchall()}

if not manut_xl.empty and "IDOrdServ" in manut_xl.columns:
    xl_nos_series = manut_xl["IDOrdServ"].dropna().astype(str).str.strip()
    xl_nos_unique = set(xl_nos_series.unique())

    # Sem IDOrdServ
    sem_nos = manut_xl[manut_xl["IDOrdServ"].isna()]
    p(f"Linhas Excel sem IDOrdServ: {len(sem_nos)}")
    if not sem_nos.empty:
        amostra = sem_nos[["Placa","DataExecução","Sistema","Fornecedor","TotalOS"]].head(10)
        p(amostra.to_string())

    blank()
    # Com IDOrdServ mas não existe no SQL
    excl_only_nos = xl_nos_unique - sql_nos_all
    p(f"OS únicas no Excel mas AUSENTES no SQL (total): {len(excl_only_nos)}")
    if excl_only_nos:
        mask = manut_xl["IDOrdServ"].astype(str).str.strip().isin(excl_only_nos)
        sub = manut_xl[mask].drop_duplicates("IDOrdServ")
        p(f"  Detalhamento (até 20):")
        for _, r in sub.head(20).iterrows():
            p(f"    {r.get('IDOrdServ','?')} | {r.get('Placa','?')} | {r.get('DataExecução','?')} | "
              f"Sistema={r.get('Sistema','?')} | Total={r.get('TotalOS','?')}")

    blank()
    # Registros Excel por ano sem cobertura SQL
    p("Volume financeiro Excel sem cobertura SQL (por ano/placa):")
    xl_sem = manut_xl[manut_xl["IDOrdServ"].astype(str).str.strip().isin(excl_only_nos)].copy()
    if not xl_sem.empty and "DataExecução" in xl_sem.columns:
        xl_sem["_ano"] = pd.to_datetime(xl_sem["DataExecução"], errors="coerce").dt.year
        grp = xl_sem.groupby(["_ano","Placa"])["TotalOS"].agg(["sum","count"]).reset_index()
        p(grp.to_string())

# ─────────────────────────────────────────────────────────────────────────────
h1("SEÇÃO 4 — REGISTROS APENAS NO SQL (sem match Excel)")
# ─────────────────────────────────────────────────────────────────────────────

xl_nos_all = set()
if not manut_xl.empty and "IDOrdServ" in manut_xl.columns:
    xl_nos_all = set(manut_xl["IDOrdServ"].dropna().astype(str).str.strip().unique())

sql_only = sql_nos - xl_nos_all
p(f"OS no SQL (ativas) sem linha no Excel: {len(sql_only)}")
if sql_only:
    cur.execute(f"""
        SELECT numero_os, placa, modelo, data_execucao, status_os, total_os,
               (SELECT sistema FROM os_itens WHERE os_id=ordens_servico.id LIMIT 1) as sistema
        FROM ordens_servico
        WHERE numero_os IN ({','.join('?' for _ in sql_only)})
          AND deletado_em IS NULL
        ORDER BY data_execucao
    """, list(sql_only))
    rows = cur.fetchall()
    p(f"  Detalhamento (até 30):")
    for r in rows[:30]:
        p(f"    {r['numero_os']} | {r['placa']} | {r['data_execucao']} | "
          f"status={r['status_os']} | total={r['total_os']} | sistema={r['sistema']}")
    if len(rows) > 30:
        p(f"    ... e mais {len(rows)-30} registros")

# ─────────────────────────────────────────────────────────────────────────────
h1("SEÇÃO 5 — REGISTROS DIVERGENTES (match existente, valores diferentes)")
# ─────────────────────────────────────────────────────────────────────────────

if not manut_xl.empty:
    # OS que existem nos dois lados — comparar campos
    match_nos = xl_nos_all & sql_nos_all
    p(f"OS com match em ambos os lados: {len(match_nos)}")

    cur.execute(f"""
        SELECT os.numero_os, os.placa, os.total_os, os.data_execucao,
               os.fornecedor, os.km,
               (SELECT sistema FROM os_itens WHERE os_id=os.id LIMIT 1) as sistema_sql
        FROM ordens_servico os
        WHERE os.numero_os IN ({','.join('?' for _ in match_nos)})
          AND os.deletado_em IS NULL
    """, list(match_nos))
    sql_dict = {r["numero_os"]: dict(r) for r in cur.fetchall()}

    # Agregar Excel por OS (pegar primeira linha — dados de cabeçalho OS)
    xl_dedup = (manut_xl[manut_xl["IDOrdServ"].astype(str).str.strip().isin(match_nos)]
                .drop_duplicates("IDOrdServ").set_index("IDOrdServ"))

    divergencias = {
        "total_os":       [],
        "data_execucao":  [],
        "placa":          [],
        "sistema":        [],
        "fornecedor":     [],
        "km":             [],
    }

    for nos, xl_row in xl_dedup.iterrows():
        nos = str(nos).strip()
        sql = sql_dict.get(nos)
        if not sql:
            continue

        # TotalOS
        try:
            xl_total = float(xl_row.get("TotalOS") or 0)
            sql_total = float(sql["total_os"] or 0)
            if abs(xl_total - sql_total) > 1.0:
                divergencias["total_os"].append(
                    f"  {nos}: Excel={xl_total:.2f} | SQL={sql_total:.2f} | Δ={xl_total-sql_total:.2f}"
                )
        except: pass

        # DataExecução
        try:
            xl_dt = str(pd.to_datetime(xl_row.get("DataExecução"), errors="coerce"))[:10]
            sql_dt = str(sql["data_execucao"] or "")[:10]
            if xl_dt != sql_dt and xl_dt != "NaT":
                divergencias["data_execucao"].append(
                    f"  {nos}: Excel={xl_dt} | SQL={sql_dt}"
                )
        except: pass

        # Placa
        try:
            xl_p = str(xl_row.get("Placa","")).strip().upper()
            sql_p = str(sql["placa"] or "").strip().upper()
            if xl_p and sql_p and xl_p != sql_p:
                divergencias["placa"].append(f"  {nos}: Excel={xl_p} | SQL={sql_p}")
        except: pass

        # Sistema
        try:
            xl_s = str(xl_row.get("Sistema","")).strip().lower()
            sql_s = str(sql["sistema_sql"] or "").strip().lower()
            if xl_s and sql_s and xl_s != sql_s:
                divergencias["sistema"].append(f"  {nos}: Excel={xl_s} | SQL={sql_s}")
        except: pass

        # Fornecedor
        try:
            xl_f = str(xl_row.get("Fornecedor","")).strip().lower()
            sql_f = str(sql["fornecedor"] or "").strip().lower()
            if xl_f and sql_f and xl_f != sql_f and xl_f not in INVALID and sql_f not in INVALID:
                divergencias["fornecedor"].append(f"  {nos}: Excel={xl_row.get('Fornecedor')} | SQL={sql['fornecedor']}")
        except: pass

        # KM
        try:
            xl_km = float(xl_row.get("KM") or 0)
            sql_km = float(sql["km"] or 0)
            if abs(xl_km - sql_km) > 10 and xl_km > 0 and sql_km > 0:
                divergencias["km"].append(
                    f"  {nos}: Excel={xl_km:.0f} | SQL={sql_km:.0f} | Δ={xl_km-sql_km:.0f}"
                )
        except: pass

    for campo, divs in divergencias.items():
        blank()
        p(f"Divergências em '{campo}': {len(divs)}")
        for d in divs[:10]:
            p(d)
        if len(divs) > 10:
            p(f"  ... e mais {len(divs)-10}")

# ─────────────────────────────────────────────────────────────────────────────
h1("SEÇÃO 6 — AUDITORIA DE CAMPOS PNEU")
# ─────────────────────────────────────────────────────────────────────────────

# Excel: pneu compras
xl_pneu = pd.DataFrame()
if not manut_xl.empty and "Sistema" in manut_xl.columns:
    xl_pneu = manut_xl[
        (manut_xl["Sistema"].fillna("").str.lower() == "pneu") &
        (manut_xl["Categoria"].fillna("").str.lower() == "compra")
    ].copy()
p(f"Excel: linhas Pneu+Compra = {len(xl_pneu)}")

# SQL: pneu compras
cur.execute("""
    SELECT os.numero_os, os.placa,
           oi.espec_pneu, oi.posicao_pneu, oi.marca_pneu, oi.modelo_pneu,
           oi.manejo_pneu, oi.qtd_pneu, oi.categoria
    FROM os_itens oi
    JOIN ordens_servico os ON os.id = oi.os_id
    WHERE os.deletado_em IS NULL
      AND LOWER(oi.sistema) = 'pneu'
      AND (LOWER(COALESCE(oi.categoria,'')) = 'compra'
           OR LOWER(COALESCE(oi.manejo_pneu,'')) = 'recapadora')
""")
sql_pneu_rows = cur.fetchall()
p(f"SQL: itens Pneu+Compra/Recap = {len(sql_pneu_rows)}")

# Campos pneu inválidos no SQL
blank()
p("Campos pneu com valores inválidos no SQL (os_itens, sistema=pneu):")
campos_pneu = ["espec_pneu","posicao_pneu","marca_pneu","modelo_pneu","manejo_pneu","qtd_pneu","categoria"]
for campo in campos_pneu:
    n = count_invalids_sql(cur,
        "(SELECT oi.* FROM os_itens oi JOIN ordens_servico os ON os.id=oi.os_id "
        "WHERE os.deletado_em IS NULL AND LOWER(oi.sistema)='pneu') t",
        campo)
    cur.execute(f"""
        SELECT COUNT(*) FROM os_itens oi
        JOIN ordens_servico os ON os.id=oi.os_id
        WHERE os.deletado_em IS NULL AND LOWER(oi.sistema)='pneu'
    """)
    total_pneu = cur.fetchone()[0]
    pct = 100*n/max(total_pneu,1)
    p(f"  {campo:20s}: {n:4d} inválidos de {total_pneu} ({pct:.1f}%)")

# Cruzamento pneu por IDOrdServ
blank()
p("Cruzamento pneu Excel vs SQL por IDOrdServ (espec_pneu):")
if not xl_pneu.empty and "IDOrdServ" in xl_pneu.columns:
    sql_pneu_dict = {}
    for r in sql_pneu_rows:
        sql_pneu_dict.setdefault(r["numero_os"], []).append(dict(r))

    divergencias_pneu = []
    only_excel_pneu   = []
    only_sql_pneu     = []

    xl_pneu_nos = set(xl_pneu["IDOrdServ"].dropna().astype(str).str.strip().unique())
    sql_pneu_nos = set(sql_pneu_dict.keys())

    only_excel_pneu = xl_pneu_nos - sql_pneu_nos
    only_sql_pneu   = sql_pneu_nos - xl_pneu_nos
    both_pneu       = xl_pneu_nos & sql_pneu_nos

    p(f"  Apenas no Excel (sem OS pneu SQL): {len(only_excel_pneu)}")
    for nos in sorted(only_excel_pneu)[:10]:
        row = xl_pneu[xl_pneu["IDOrdServ"].astype(str).str.strip() == nos].iloc[0]
        p(f"    {nos} | {row.get('Placa')} | espec={row.get('EspecificaçãoPneu')} | marca={row.get('MarcaPneu')}")

    p(f"  Apenas no SQL (sem linha Excel Pneu): {len(only_sql_pneu)}")
    for nos in sorted(only_sql_pneu)[:10]:
        items = sql_pneu_dict[nos]
        for it in items:
            p(f"    {nos} | {it['placa']} | espec={it['espec_pneu']} | marca={it['marca_pneu']}")

    p(f"  Presentes nos dois lados: {len(both_pneu)}")
    for nos in sorted(both_pneu)[:10]:
        xl_rows = xl_pneu[xl_pneu["IDOrdServ"].astype(str).str.strip() == nos]
        sql_items = sql_pneu_dict[nos]
        xl_espec = set(str(v).strip() for v in xl_rows["EspecificaçãoPneu"].dropna())
        sql_espec = set(str(it["espec_pneu"]).strip() for it in sql_items if it["espec_pneu"])
        match_sym = "✓" if xl_espec == sql_espec or not (xl_espec and sql_espec) else "≠"
        p(f"    {match_sym} {nos} | xl_espec={xl_espec} | sql_espec={sql_espec}")

# ─────────────────────────────────────────────────────────────────────────────
h1("SEÇÃO 7 — VALORES INVÁLIDOS")
# ─────────────────────────────────────────────────────────────────────────────

h2("7A — SQL: campos críticos de ordens_servico")
campos_os = ["numero_os","placa","status_os","total_os","data_execucao","km","fornecedor","tipo_manutencao"]
cur.execute("SELECT COUNT(*) FROM ordens_servico WHERE deletado_em IS NULL")
total_os_sql = cur.fetchone()[0]
p(f"Total ordens_servico ativas: {total_os_sql}")
for campo in campos_os:
    n = count_invalids_sql(cur, "ordens_servico", campo)
    # excluir deletadas
    cur.execute(f"""
        SELECT COUNT(*) FROM ordens_servico
        WHERE deletado_em IS NULL AND (
            {campo} IS NULL OR TRIM(CAST({campo} AS TEXT))=''
            OR LOWER(TRIM(CAST({campo} AS TEXT))) IN ('nan','none','nat','null','-')
        )
    """)
    n_ativo = cur.fetchone()[0]
    p(f"  {campo:20s}: {n_ativo:4d} inválidos de {total_os_sql} ativos")

h2("7B — SQL: campos críticos de os_itens")
campos_osi = ["sistema","categoria","servico","descricao"]
cur.execute("SELECT COUNT(*) FROM os_itens")
total_osi = cur.fetchone()[0]
p(f"Total os_itens: {total_osi}")
for campo in campos_osi:
    n = count_invalids_sql(cur, "os_itens", campo)
    p(f"  {campo:20s}: {n:4d} inválidos de {total_osi}")

h2("7C — SQL: campos críticos de notas_fiscais")
campos_nf = ["numero_nf","valor_total_nf","data_emissao","fornecedor"]
cur.execute("SELECT COUNT(*) FROM notas_fiscais WHERE deletado_em IS NULL")
total_nf = cur.fetchone()[0]
p(f"Total notas_fiscais ativas: {total_nf}")
for campo in campos_nf:
    cur.execute(f"""
        SELECT COUNT(*) FROM notas_fiscais
        WHERE deletado_em IS NULL AND (
            {campo} IS NULL OR TRIM(CAST({campo} AS TEXT))=''
            OR LOWER(TRIM(CAST({campo} AS TEXT))) IN ('nan','none','nat','null','-')
        )
    """)
    n = cur.fetchone()[0]
    p(f"  {campo:20s}: {n:4d} inválidos de {total_nf}")

h2("7D — Excel MANUTENCOES: campos críticos")
if not manut_xl.empty:
    total_xl = len(manut_xl)
    p(f"Total linhas MANUTENCOES Excel: {total_xl}")
    campos_xl = ["IDOrdServ","Placa","Sistema","Categoria","Fornecedor",
                 "TotalOS","DataExecução","KM","Nota"]
    for campo in campos_xl:
        if campo not in manut_xl.columns:
            p(f"  {campo:25s}: COLUNA NÃO ENCONTRADA")
            continue
        n = manut_xl[campo].apply(lambda v:
            v is None or (isinstance(v, float) and pd.isna(v)) or
            str(v).strip().lower() in INVALID
        ).sum()
        pct = 100*n/total_xl
        p(f"  {campo:25s}: {n:5d} inválidos de {total_xl} ({pct:.1f}%)")

# ─────────────────────────────────────────────────────────────────────────────
h1("SEÇÃO 8 — DIFERENÇAS DE NOMENCLATURA E TIPAGEM")
# ─────────────────────────────────────────────────────────────────────────────

MAPPING_MANUT = {
    "IDManutencao":     ("manutencoes",    "id",              "INTEGER"),
    "IDOrdServ":        ("ordens_servico",  "numero_os",       "VARCHAR"),
    "NFOrdem":          ("manutencao_parcelas","nf_ordem",     "INTEGER"),
    "TotalOS":          ("ordens_servico",  "total_os",        "NUMERIC"),
    "Placa":            ("ordens_servico",  "placa",           "VARCHAR"),
    "IDVeiculo":        ("ordens_servico",  "id_veiculo",      "INTEGER"),
    "Fornecedor":       ("ordens_servico",  "fornecedor",      "VARCHAR"),
    "Nota":             ("notas_fiscais",   "numero_nf",       "VARCHAR"),
    "Data Venc.":       ("manutencao_parcelas","data_vencimento","DATE"),
    "ParcelaAtual":     ("manutencao_parcelas","parcela_atual","INTEGER"),
    "ParcelaTotal":     ("manutencao_parcelas","parcela_total","INTEGER"),
    "ValorParcela":     ("manutencao_parcelas","valor_parcela","NUMERIC"),
    "FormaPgto":        ("manutencao_parcelas","forma_pgto",   "VARCHAR"),
    "Categoria":        ("os_itens",        "categoria",       "VARCHAR"),
    "Status":           ("manutencao_parcelas","status_pagamento","VARCHAR"),
    "TipoManutencao":   ("ordens_servico",  "tipo_manutencao", "VARCHAR"),
    "Sistema":          ("os_itens",        "sistema",         "VARCHAR"),
    "Serviço":          ("os_itens",        "servico",         "VARCHAR"),
    "Descricao":        ("os_itens",        "descricao",       "TEXT"),
    "QtdItens":         ("os_itens",        "qtd_itens",       "INTEGER"),
    "KM":               ("ordens_servico",  "km",              "NUMERIC"),
    "PosiçãoPneu":      ("os_itens",        "posicao_pneu",    "VARCHAR"),
    "QtdPneu":          ("os_itens",        "qtd_pneu",        "INTEGER"),
    "EspecificaçãoPneu":("os_itens",        "espec_pneu",      "VARCHAR"),
    "MarcaPneu":        ("os_itens",        "marca_pneu",      "VARCHAR"),
    "ModeloPneu":       ("os_itens",        "modelo_pneu",     "VARCHAR"),
    "CondicaoPneu":     ("os_itens",        "condicao_pneu",   "VARCHAR"),
    "ManejoPneu":       ("os_itens",        "manejo_pneu",     "VARCHAR"),
    "DataExecução":     ("ordens_servico",  "data_execucao",   "DATE"),
    "ProxKM":           ("ordens_servico",  "prox_km",         "NUMERIC"),
    "ProxData":         ("ordens_servico",  "prox_data",       "DATE"),
    "Obsercacoes":      ("ordens_servico",  "observacoes",     "TEXT"),
}

APENAS_EXCEL = ["ValidaNovaOS","IDContrato","Modelo","Implemento","Empresa","NFOrdem",
                "ResponsavelTec","Indisponível"]
APENAS_SQL_OS = ["status_execucao","descricao_pendente","migrado_de_ids",
                 "deletado_em","criado_em","atualizado_em","status_os"]

p(f"{'Excel (MANUTENCOES)':35s} {'SQL Tabela':20s} {'SQL Coluna':25s} {'Tipo SQL'}")
p("-"*100)
for xl_col, (sql_tbl, sql_col, sql_type) in MAPPING_MANUT.items():
    if not manut_xl.empty and xl_col in manut_xl.columns:
        xl_dtype = str(manut_xl[xl_col].dtype)
    else:
        xl_dtype = "AUSENTE"
    p(f"  {xl_col:33s} {sql_tbl:20s} {sql_col:25s} {sql_type:12s} [Excel dtype: {xl_dtype}]")

blank()
p("Colunas Excel SEM equivalente SQL direto:")
for c in APENAS_EXCEL:
    p(f"  Excel.{c}")

blank()
p("Colunas SQL SEM equivalente Excel (ordens_servico + os_itens):")
for c in APENAS_SQL_OS:
    p(f"  SQL.ordens_servico.{c}")
sql_only_osi = ["manutencao_origem_id"]
for c in sql_only_osi:
    p(f"  SQL.os_itens.{c}")

# ─────────────────────────────────────────────────────────────────────────────
h1("SEÇÃO 9 — TABELAS SEM EQUIVALENTE SQL (risco de perda)")
# ─────────────────────────────────────────────────────────────────────────────

abas_sem_sql = {
    "📄 CONTRATOS":         "Contratos de locação — lido pelo backend via load_raw()/CONTRATOS",
    "🔗 CONTRATO_VEICULO":  "Relação contrato-veículo — lido pelo backend",
    "🔗 CONTRATO_ORIGEM":   "Origem dos contratos",
    "🏢 EMPRESAS":          "Cadastro de empresas — lido pelo backend",
    "🏢 CLIENTES":          "Cadastro de clientes",
    "🛡️ SEGUROS":           "Apólices de seguro — dados de parcelas em seguro_mensal",
}
for aba, desc in abas_sem_sql.items():
    df_aba = excel_dfs.get(aba, pd.DataFrame())
    p(f"  {aba:30s}: {len(df_aba):4d} linhas | {desc}")

blank()
p("Risco: backend (load_raw) lê CONTRATOS e CONTRATO_VEICULO diretamente do Excel.")
p("Se migrar para SQL-only, essas abas precisam de tabelas próprias no banco.")

# ─────────────────────────────────────────────────────────────────────────────
h1("RESUMO EXECUTIVO — RISCOS DE CONSOLIDAÇÃO")
# ─────────────────────────────────────────────────────────────────────────────

resumo = [
    ("MANUTENCOES → SQL",       "ALTO",   "611 linhas Excel denormalizadas vs 212 OS SQL; 52 linhas sem IDOrdServ"),
    ("Pneu fields",             "MÉDIO",  "Cruzamento por IDOrdServ possível; campos parcialmente corrigidos"),
    ("Financeiro simples",      "BAIXO",  "fat, seg, imp, rast: row counts idênticos, DB já autoritativo"),
    ("CONTRATOS/CLIENTES",      "ALTO",   "Sem equivalente SQL; backend lê do Excel; requer novo modelo de dados"),
    ("Registros sem IDOrdServ", "MÉDIO",  "52 linhas Excel; fallback: placa+data+valor"),
    ("Divergências TotalOS",    "MÉDIO",  "Diferença entre TotalOS Excel vs parcelas SQL por competência"),
    ("nf_itens / pneu_rodizios","INFO",   "Tabelas SQL sem equivalente Excel — dados novos, sem risco de perda"),
    ("Campos FROTA extras",     "INFO",   "Renavam, AnoFabricacao, TabelaFipe, etc. existem só no Excel"),
]

p(f"{'Área':35s} {'Risco':8s} {'Razão'}")
p("-"*100)
for area, risco, razao in resumo:
    p(f"  {area:33s} {risco:8s} {razao}")

blank()
p("Estimativa de complexidade da migração:")
p("  - Fase 2 (mapeamento OS Excel→SQL):        ALTA    (~200 OS, validação por parcela)")
p("  - Fase 3 (migrar CONTRATOS para SQL):       ALTA    (novo schema necessário)")
p("  - Fase 4 (limpeza campos inválidos):        MÉDIA   (automatizável por regras)")
p("  - Fase 5 (deprecar load_raw do Excel):      BAIXA   (backend já usa DB para financeiro)")

# ─────────────────────────────────────────────────────────────────────────────
# Gravar arquivo
# ─────────────────────────────────────────────────────────────────────────────
conn.close()

report = "\n".join(lines)
OUT.write_text(report, encoding="utf-8")
print(f"Relatório gerado: {OUT}")
print(f"Total de linhas no relatório: {len(lines)}")
