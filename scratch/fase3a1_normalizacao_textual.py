"""
FASE 3A.1 — Script 2: Normalização Textual (DRY-RUN APENAS)
Nenhum UPDATE/INSERT/DELETE é executado.
Simula normalização de texto em fornecedor, sistema, servico, categoria.
Output: scratch/dryrun_normalizacao.txt
"""
import sys, io, sqlite3, os, unicodedata
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "locadora.db")
OUT_PATH = os.path.join(os.path.dirname(__file__), "dryrun_normalizacao.txt")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

lines = []
def w(s=""): lines.append(s)

# ── Funções de normalização ────────────────────────────────────────────────────

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

def normalize_sistema(v):
    ALIASES = {
        'pneu': 'Pneu', 'PNEU': 'Pneu',
        'motor': 'Motor', 'MOTOR': 'Motor',
        'revisao': 'Revisao', 'revisão': 'Revisao', 'REVISAO': 'Revisao',
        'freio': 'Freio', 'FREIO': 'Freio',
        'elétrico': 'Eletrico', 'eletrico': 'Eletrico', 'ELETRICO': 'Eletrico',
        'direção': 'Direcao', 'direcao': 'Direcao', 'DIRECAO': 'Direcao',
        'câmbio': 'Cambio', 'cambio': 'Cambio', 'CAMBIO': 'Cambio',
        'hidráulico': 'Hidraulico', 'hidraulico': 'Hidraulico',
        'suspensão': 'Suspensao', 'suspensao': 'Suspensao',
        'arrefecimento': 'Arrefecimento', 'diferencial': 'Diferencial',
        'implemento': 'Implemento', 'guincho': 'Guincho', 'outro': 'Outro',
        'diversos': 'Diversos', 'DIVERSOS': 'Diversos',
    }
    v = normalize_text(v)
    if not v:
        return None
    return ALIASES.get(v, ALIASES.get(v.lower(), v.title()))

def normalize_categoria(v):
    ALIASES = {
        'compra': 'Compra', 'COMPRA': 'Compra', 'Compra': 'Compra',
        'serviço': 'Servico', 'servico': 'Servico', 'SERVICO': 'Servico', 'Servico': 'Servico',
        'serviço': 'Servico',
        'MONTAGEM E ALINHAMENTO PNEUS': 'Servico',
        'MONTAGEM E BALANCEAMENTO PNEUS': 'Servico',
        'M.O. PNEUS': 'Servico', 'M.O PNEUS': 'Servico',
    }
    v = normalize_text(v)
    if not v:
        return None
    return ALIASES.get(v, v)

# ── Analisar cada tabela/campo ──────────────────────────────────────────────────

def analisar_campo(tabela, campo, norm_fn, id_col="id", where=""):
    cur.execute(f"SELECT {id_col}, {campo} FROM {tabela} {where} ORDER BY {id_col}")
    rows = cur.fetchall()
    resultados = []
    colisoes = {}
    for row_id, val in rows:
        normalizado = norm_fn(val)
        val_str = str(val) if val is not None else "(NULL)"
        norm_str = str(normalizado) if normalizado is not None else "(NULL)"
        mudou = (val_str.strip() != norm_str.strip()) if val is not None else False
        resultados.append((row_id, val_str, norm_str, mudou))
        if normalizado:
            key = normalizado.upper()
            if key not in colisoes:
                colisoes[key] = set()
            colisoes[key].add(val_str)
    return resultados, colisoes

def escrever_secao(titulo, tabela, campo, norm_fn, id_col="id", where=""):
    w("-" * 60)
    w(f"--- {titulo} ---")
    resultados, colisoes = analisar_campo(tabela, campo, norm_fn, id_col, where)
    com_mudanca = [(rid, ant, dep, m) for rid, ant, dep, m in resultados if m]
    w(f"Total registros: {len(resultados)} | Com mudança: {len(com_mudanca)}")
    w()
    if com_mudanca:
        w(f"  {'id':>8}  {'valor_atual':<50}  {'normalizado':<50}  mudou?")
        w("  " + "-" * 120)
        for rid, ant, dep, m in com_mudanca[:30]:  # mostrar até 30
            w(f"  {rid:>8}  {ant:<50}  {dep:<50}  SIM")
        if len(com_mudanca) > 30:
            w(f"  ... e mais {len(com_mudanca) - 30} registros com mudança")
    else:
        w("  (Nenhuma mudança necessária)")
    w()

    # Colisões: diferentes valores que normalizam para o mesmo resultado
    colisoes_reais = {k: v for k, v in colisoes.items() if len(v) > 1}
    if colisoes_reais:
        w("  POSSÍVEIS COLISÕES (valores distintos que normalizam igual):")
        for canonical, originals in sorted(colisoes_reais.items()):
            orig_list = " | ".join(f'"{o}"' for o in sorted(originals))
            status = "[OK]" if len({o.upper().strip() for o in originals}) == 1 else "[REVISAR]"
            w(f"  {status} → '{canonical}': {orig_list}")
    w()
    return com_mudanca, colisoes_reais

# ── Cabeçalho ──────────────────────────────────────────────────────────────────
w("=" * 80)
w("FASE 3A.1 — SIMULAÇÃO DE NORMALIZAÇÃO TEXTUAL (DRY-RUN)")
w(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
w("NENHUM UPDATE FOI EXECUTADO.")
w("=" * 80)
w()

total_mudancas = 0
total_colisoes = 0

# 1. ordens_servico.fornecedor
m, c = escrever_secao("ordens_servico.fornecedor", "ordens_servico", "fornecedor", normalize_fornecedor)
total_mudancas += len(m); total_colisoes += len(c)

# 2. notas_fiscais.fornecedor
m, c = escrever_secao("notas_fiscais.fornecedor", "notas_fiscais", "fornecedor", normalize_fornecedor)
total_mudancas += len(m); total_colisoes += len(c)

# 3. manutencao_parcelas.fornecedor
m, c = escrever_secao("manutencao_parcelas.fornecedor", "manutencao_parcelas", "fornecedor", normalize_fornecedor)
total_mudancas += len(m); total_colisoes += len(c)

# 4. os_itens.sistema
m, c = escrever_secao("os_itens.sistema", "os_itens", "sistema", normalize_sistema)
total_mudancas += len(m); total_colisoes += len(c)

# 5. os_itens.categoria (inclui mapeamento de categorias não-padrão)
m, c = escrever_secao("os_itens.categoria (inclui aliases de categoria)",
                       "os_itens", "categoria", normalize_categoria)
total_mudancas += len(m); total_colisoes += len(c)

# 6. os_itens.servico — apenas normalização básica
m, c = escrever_secao("os_itens.servico (normalização básica)", "os_itens", "servico", normalize_text)
total_mudancas += len(m); total_colisoes += len(c)

# ── Resumo ─────────────────────────────────────────────────────────────────────
w("=" * 80)
w("RESUMO GERAL DE NORMALIZAÇÃO")
w("=" * 80)
w(f"  Total de registros com mudança identificada : {total_mudancas}")
w(f"  Total de grupos com possíveis colisões      : {total_colisoes}")
w()
w("PRÓXIMO PASSO: Revisar colisões marcadas [REVISAR] antes de aplicar normalização.")
w("Nenhuma alteração foi feita neste script.")

conn.close()

output = "\n".join(lines)
print(output)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(output)
print(f"\nRelatório salvo em: {OUT_PATH}", file=sys.stderr)
