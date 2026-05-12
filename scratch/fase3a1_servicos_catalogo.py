"""
FASE 3A.1 — Script 4: Catálogo de Serviços (DRY-RUN APENAS)
Nenhum UPDATE/INSERT/DELETE é executado.
Propõe catálogo normalizado de serviços com aliases e agrupamentos.
Output: scratch/dryrun_servicos.txt
"""
import sys, io, sqlite3, os, unicodedata, re
from collections import defaultdict
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "locadora.db")
OUT_PATH = os.path.join(os.path.dirname(__file__), "dryrun_servicos.txt")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

lines = []
def w(s=""): lines.append(s)

# ── Normalização para comparação ───────────────────────────────────────────────
def norm_cmp(v):
    """Normaliza para comparação semântica (lowercase, sem acentos, sem pontuação extra)."""
    if not v or str(v).strip().lower() in ('nan', 'none', '-', '', 'null'):
        return None
    v = str(v).strip().lower()
    v = unicodedata.normalize('NFD', v).encode('ascii', 'ignore').decode('ascii')
    v = re.sub(r'[.\-+]', ' ', v)
    v = ' '.join(v.split())
    return v

# ── Coletar todos os serviços de os_itens ────────────────────────────────────
cur.execute("""
    SELECT oi.servico, oi.sistema, oi.categoria, COUNT(*) as qtd
    FROM os_itens oi
    WHERE oi.servico IS NOT NULL AND TRIM(oi.servico) != ''
    GROUP BY LOWER(TRIM(oi.servico))
    ORDER BY qtd DESC
""")
servicos_raw = cur.fetchall()

# ── Grupos de serviços por padrão semântico ────────────────────────────────────
# Cada grupo: (nome_canonico_sugerido, sistema, categoria, palavras_chave, confiança)
GRUPOS_DEFINICAO = [
    ("Fornecimento de Pneus",           "Pneu",          "Compra",  ["fornec", "pneu", "pneus"],                   "ALTA"),
    ("Montagem e Alinhamento de Pneus", "Pneu",          "Servico", ["montagem", "alinhamento", "m o pneu"],       "ALTA"),
    ("Balanceamento de Pneus",          "Pneu",          "Servico", ["balance", "balanceamento"],                   "ALTA"),
    ("Substituição de Pastilhas",       "Freio",         "Compra",  ["pastilha", "past"],                           "ALTA"),
    ("Substituição de Lonas",           "Freio",         "Compra",  ["lona", "lonas"],                              "ALTA"),
    ("Substituição de Disco de Freio",  "Freio",         "Compra",  ["disco", "discos"],                            "ALTA"),
    ("Kit Revisão",                     "Revisao",       "Compra",  ["kit revisao", "kit rev"],                     "ALTA"),
    ("Troca de Óleo e Filtros",         "Motor",         "Compra",  ["oleo", "filtro", "oleo e filtro"],           "ALTA"),
    ("Kit Embreagem",                   "Cambio",        "Compra",  ["embreagem", "kit embreagem"],                 "ALTA"),
    ("Substituição de Correia",         "Motor",         "Compra",  ["correia", "dentada", "alternador"],           "MEDIA"),
    ("Serviço Elétrico",                "Eletrico",      "Servico", ["eletrica", "eletrico", "lampada", "bateria"], "MEDIA"),
    ("Serviço de Direção",              "Direcao",       "Servico", ["direcao", "hidraulic", "bomba direcao"],      "MEDIA"),
    ("Serviço de Motor",                "Motor",         "Servico", ["motor", "injecao", "cabecote"],               "MEDIA"),
    ("Serviço Hidráulico",              "Hidraulico",    "Servico", ["hidraulic"],                                  "MEDIA"),
    ("Guincho / Socorro",               "Guincho",       "Servico", ["guincho", "socorro", "reboque"],              "ALTA"),
    ("Serviço Diversos",                "Diversos",      "Servico", ["servico", "manutencao", "reparo"],            "BAIXA"),
]

def match_grupo(servico_norm):
    if not servico_norm:
        return None, 0
    melhor = None
    melhor_score = 0
    for nome, sistema, cat, palavras, conf in GRUPOS_DEFINICAO:
        score = sum(1 for p in palavras if p in servico_norm)
        if score > melhor_score:
            melhor_score = score
            melhor = (nome, sistema, cat, conf)
    return melhor, melhor_score

# ── Agrupar serviços ─────────────────────────────────────────────────────────
grupos_resultado = defaultdict(list)
sem_grupo = []

for servico, sistema, categoria, qtd in servicos_raw:
    sn = norm_cmp(servico)
    grupo, score = match_grupo(sn)
    if grupo and score >= 1:
        grupos_resultado[grupo[0]].append((servico, sistema, categoria, qtd, grupo[1], grupo[2], grupo[3]))
    else:
        sem_grupo.append((servico, sistema, categoria, qtd))

# ── Escrever relatório ─────────────────────────────────────────────────────────
w("=" * 80)
w("FASE 3A.1 — PROPOSTA DE CATÁLOGO DE SERVIÇOS (DRY-RUN)")
w(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
w("NENHUM UPDATE FOI EXECUTADO.")
w("=" * 80)
w()
w(f"Total de valores únicos de servico: {len(servicos_raw)}")
w(f"Grupos identificados com match:     {len(grupos_resultado)}")
w(f"Serviços sem grupo definido:        {len(sem_grupo)}")
w()

# Grupos ordenados por total de ocorrências
grupos_sorted = sorted(grupos_resultado.items(),
                       key=lambda kv: -sum(r[3] for r in kv[1]))

for nome_canonico, membros in grupos_sorted:
    total_qtd = sum(r[3] for r in membros)
    confs = {r[6] for r in membros}
    conf_str = "/".join(sorted(confs))
    sistema_sugerido = membros[0][4]
    cat_sugerida = membros[0][5]
    w("-" * 60)
    w(f'GRUPO: "{nome_canonico}"')
    w(f"  sistema: {sistema_sugerido} | categoria: {cat_sugerida} | confiança: {conf_str} | total: {total_qtd} ocorrências")
    w("  aliases encontrados:")
    for servico, sistema, cat, qtd, _, _, _ in sorted(membros, key=lambda x: -x[3]):
        diff_sis = f" [sistema diferente: {sistema}]" if sistema and sistema != sistema_sugerido else ""
        diff_cat = f" [categoria: {cat}]" if cat and cat != cat_sugerida else ""
        w(f'    → "{servico}" ({qtd}x){diff_sis}{diff_cat}')
    w()

# Sem grupo
w("=" * 80)
w(f"--- SERVIÇOS SEM GRUPO IDENTIFICADO ({len(sem_grupo)}) — texto completamente livre ---")
w()
for servico, sistema, cat, qtd in sorted(sem_grupo, key=lambda x: -x[3]):
    cat_str = cat or "(NULL)"
    w(f'  "{servico}" | {sistema} | {cat_str} | {qtd}x')
w()

# Resumo
w("=" * 80)
w("RESUMO")
w("=" * 80)
alta = sum(1 for kv in grupos_resultado.items() if any(r[6] == "ALTA" for r in kv[1]))
media = sum(1 for kv in grupos_resultado.items() if any(r[6] == "MEDIA" for r in kv[1]))
w(f"  Grupos de alta confiança : {alta}")
w(f"  Grupos de média confiança: {media}")
w(f"  Serviços sem grupo       : {len(sem_grupo)}")
w()
w("PRÓXIMO PASSO: Revisar grupos e confirmar nomes canônicos antes de criar catalogo_servicos.")
w("Nenhuma alteração foi feita neste script.")

conn.close()

output = "\n".join(lines)
print(output)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(output)
print(f"\nRelatório salvo em: {OUT_PATH}", file=sys.stderr)
