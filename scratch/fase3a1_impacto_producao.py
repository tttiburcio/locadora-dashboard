"""
FASE 3A.1 — Script 6: Mapa de Dependências Excel no Backend (DRY-RUN APENAS)
Nenhum UPDATE/INSERT/DELETE é executado.
Lê main.py e mapeia dependências do Excel ainda ativas.
Output: scratch/dryrun_impacto.txt
"""
import sys, io, sqlite3, os, re
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB_PATH   = os.path.join(os.path.dirname(__file__), "..", "locadora.db")
MAIN_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "main.py")
OUT_PATH  = os.path.join(os.path.dirname(__file__), "dryrun_impacto.txt")

lines = []
def w(s=""): lines.append(s)

# ── Ler main.py ───────────────────────────────────────────────────────────────
with open(MAIN_PATH, "r", encoding="utf-8") as f:
    main_src = f.read()
main_lines = main_src.splitlines()

# ── Buscar dependências explícitas ─────────────────────────────────────────────
ABAS_EXCEL = [
    "frota", "fat_unitario", "reembolsos", "manutencoes", "faturamento",
    "seguro_mensal", "impostos", "rastreamento", "contratos",
    "clientes", "empresas", "contrato_veiculo",
]

ENDPOINTS = [
    ("/api/years",          r"def get_years"),
    ("/api/kpis",           r"def get_kpis"),
    ("/api/monthly",        r"def get_monthly"),
    ("/api/vehicles",       r"def get_vehicles"),
    ("/api/vehicle/{placa}",r"def get_vehicle"),
    ("/api/manutencao",     r"def (get|post|put|delete)_manutencao"),
    ("/api/nf",             r"def (get|post|put|delete)_nf"),
]

def buscar_linhas(padrao):
    """Retorna lista de (numero_linha, conteudo) onde padrao ocorre."""
    resultado = []
    for i, linha in enumerate(main_lines, 1):
        if re.search(padrao, linha, re.IGNORECASE):
            resultado.append((i, linha.rstrip()))
    return resultado

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
w("=" * 80)
w("FASE 3A.1 — MAPA DE DEPENDÊNCIAS EXCEL ATIVAS NO BACKEND (DRY-RUN)")
w(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
w(f"Arquivo analisado: {MAIN_PATH}")
w("NENHUMA ALTERAÇÃO FOI FEITA.")
w("=" * 80)
w()

# ── 1. Abas lidas via load_raw / SHEETS ───────────────────────────────────────
w("-" * 60)
w("--- ABAS EXCEL AINDA CARREGADAS VIA load_raw() ---")
w()

sheets_match = buscar_linhas(r'"[🚛💰↩️🔧🧾📋📍🔗🏢🛡️]')
w(f"  Definição de SHEETS em main.py (linhas):")
for lnum, linha in sheets_match:
    w(f"  L{lnum:>5}: {linha.strip()}")
w()

# Status por aba
STATUS = {
    "frota":             ("HÍBRIDO",    "SQL merge em compute() — Excel ainda lido como base"),
    "manutencoes":       ("HÍBRIDO",    "SQL OS integradas, mas Excel ainda como fallback"),
    "fat_unitario":      ("SQL PREFER", "_load_db_financials() — fallback Excel se SQL vazio"),
    "seguro_mensal":     ("SQL PREFER", "_load_db_financials() — fallback Excel se SQL vazio"),
    "impostos":          ("SQL PREFER", "_load_db_financials() — fallback Excel se SQL vazio"),
    "rastreamento":      ("SQL PREFER", "_load_db_financials() — fallback Excel se SQL vazio"),
    "reembolsos":        ("EXCEL PURO", "compute() lê Excel direto — SQL existe mas não é usado"),
    "faturamento":       ("EXCEL PURO", "compute() lê Excel direto — SQL existe mas não é usado"),
    "contratos":         ("EXCEL PURO", "_contrato_ativo() — sem equivalente SQL"),
    "contrato_veiculo":  ("EXCEL PURO", "_contrato_ativo() — sem equivalente SQL"),
    "empresas":          ("EXCEL PURO", "_empresa_nome() — sem equivalente SQL"),
    "clientes":          ("EXCEL PURO", "lido mas não referenciado em nenhum endpoint"),
}

w(f"  {'aba':<20}  {'status':<14}  observação")
w("  " + "-" * 90)
for aba, (status, obs) in STATUS.items():
    marcador = "⚠️ " if "EXCEL PURO" in status else "→ "
    w(f"  {aba:<20}  {status:<14}  {obs}")
w()

# ── 2. Funções que ainda dependem do Excel ────────────────────────────────────
w("-" * 60)
w("--- FUNÇÕES COM DEPENDÊNCIA DIRETA DO EXCEL ---")
w()

FUNCOES = {
    "_empresa_nome": "data.get(\"empresas\"",
    "_contrato_ativo": "data.get(\"contratos\"",
    "compute": "data[\"reembolsos\"|\"faturamento\"",
}

for fn in ["_empresa_nome", "_contrato_ativo", "compute", "load_raw"]:
    ocorrencias = buscar_linhas(rf"def {fn}|data\[.{fn[:8]}|data\.get\(.{fn[:8]}")
    fn_lines = buscar_linhas(rf'data\.(get|__getitem__)\s*\(\s*["\']({fn[:6]})')
    dependencias = buscar_linhas(rf'data\[.*(reembolsos|faturamento|contratos|empresas|clientes)')
    if fn == "compute":
        refs = dependencias
    else:
        refs = buscar_linhas(rf'data\["({fn}|empresas|contratos|contrato_veiculo)"\]|data\.get\("({fn}|empresas|contratos)')

    def_lines = buscar_linhas(rf'def {fn}\s*\(')
    if def_lines:
        lnum = def_lines[0][0]
        w(f"  {fn}() — definida na linha {lnum}")
        if fn == "_empresa_nome":
            deps = buscar_linhas(r'data.*empresas')
            for l, c in deps[:5]:
                w(f"    L{l}: {c.strip()}")
        elif fn == "_contrato_ativo":
            deps = buscar_linhas(r'data.*(contratos|contrato_veiculo)')
            for l, c in deps[:5]:
                w(f"    L{l}: {c.strip()}")
        elif fn == "compute":
            deps = buscar_linhas(r'data\["(reembolsos|faturamento)"')
            for l, c in deps[:5]:
                w(f"    L{l}: {c.strip()}")
        w()

# ── 3. Verificar dados SQL de reembolsos e faturamento ────────────────────────
w("-" * 60)
w("--- VERIFICAÇÃO: SQL.reembolsos e SQL.faturamento têm dados? ---")
w()
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

for tabela, col_data in [("reembolsos", "emissao"), ("faturamento", "emissao")]:
    cur.execute(f"SELECT COUNT(*), MIN({col_data}), MAX({col_data}) FROM {tabela}")
    cnt, data_min, data_max = cur.fetchone()
    w(f"  {tabela}: {cnt} registros | período: {data_min} → {data_max}")

w()
w("  → Se SQL.reembolsos e SQL.faturamento têm dados completos,")
w("    é SEGURO remover o fallback Excel para essas tabelas na Fase 3A.2.")
w()

# ── 4. Endpoints afetados por aba ────────────────────────────────────────────
w("-" * 60)
w("--- ENDPOINTS AFETADOS POR ABA EXCEL ---")
w()
ENDPOINT_MAP = {
    "reembolsos":       ["/api/kpis", "/api/vehicle/{placa}"],
    "faturamento":      ["/api/kpis", "/api/monthly"],
    "contratos":        ["/api/vehicle/{placa} (via _contrato_ativo)"],
    "contrato_veiculo": ["/api/vehicle/{placa} (via _contrato_ativo)"],
    "empresas":         ["/api/vehicle/{placa} (via _empresa_nome)"],
    "clientes":         ["(nenhum endpoint — lido mas não usado)"],
}
for aba, endpoints in ENDPOINT_MAP.items():
    w(f"  {aba:<20}: {', '.join(endpoints)}")
w()

# ── 5. Pré-requisitos para remover cada aba ───────────────────────────────────
w("-" * 60)
w("--- PRÉ-REQUISITOS ANTES DE REMOVER CADA ABA DO EXCEL ---")
w()
PREREQS = {
    "reembolsos":       "Confirmar SQL.reembolsos completo (✓ verificado acima) — pronto para Fase 3A.2",
    "faturamento":      "Confirmar SQL.faturamento completo (✓ verificado acima) — pronto para Fase 3A.2",
    "contratos":        "Criar tabelas SQL contratos + contrato_veiculo (Fase 3C)",
    "contrato_veiculo": "Criar tabelas SQL contratos + contrato_veiculo (Fase 3C)",
    "empresas":         "Criar tabela SQL empresas ou migrar para campo em frota (Fase 3C)",
    "clientes":         "Sem dependência de endpoint — pode ser removido a qualquer momento",
    "frota":            "Migrar campos extras (Renavam, AnoFab, etc.) para SQL.frota (Fase 3C)",
    "manutencoes":      "Deprecar após migração completa de OS para SQL (Fase 5)",
}
for aba, prereq in PREREQS.items():
    w(f"  {aba:<20}: {prereq}")
w()

# ── 6. Impacto simulado de remoção ───────────────────────────────────────────
w("-" * 60)
w("--- IMPACTO SIMULADO DE REMOÇÃO (estimativa) ---")
w()
cur.execute("SELECT COUNT(DISTINCT id_veiculo) FROM reembolsos WHERE emissao IS NOT NULL")
veic_reimb = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM reembolsos")
total_reimb = cur.fetchone()[0]
w(f"  Se remover reembolsos do Excel e SQL falhar: {veic_reimb} veículos perdem custo_reembolsos ({total_reimb} registros)")

cur.execute("SELECT COUNT(*) FROM faturamento")
total_fat = cur.fetchone()[0]
w(f"  Se remover faturamento do Excel e SQL falhar: {total_fat} registros de faturamento global perdem visibilidade")
w(f"  Se remover contratos do Excel sem SQL: VehicleModal perde dados de Contrato/Região para TODOS os veículos")
w()

conn.close()

w("=" * 80)
w("RESUMO DE RISCO")
w("=" * 80)
w("  Abas 100% Excel puro (sem SQL equivalente): contratos, contrato_veiculo, empresas, clientes")
w("  Abas com SQL pronto mas backend ainda usa Excel: reembolsos, faturamento")
w("  Abas híbridas (SQL + Excel): frota, manutencoes, fat_unitario, seguro_mensal, impostos, rastreamento")
w()
w("AÇÃO RECOMENDADA PARA FASE 3A.2:")
w("  Apenas: remover fallback Excel de reembolsos e faturamento em compute()")
w("  Tudo mais: aguardar Fase 3C (criação das tabelas SQL de contratos/empresas)")
w("  Nenhuma alteração foi feita neste script.")

output = "\n".join(lines)
print(output)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(output)
print(f"\nRelatório salvo em: {OUT_PATH}", file=sys.stderr)
