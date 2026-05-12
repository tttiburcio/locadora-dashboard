"""
FASE 3A.2 — Execução Controlada do Saneamento
PRIMEIRA FASE COM ESCRITA REAL NO BANCO.
Apenas alterações seguras, reversíveis e determinísticas, validadas no dry-run.

Alterações:
  - os_itens.categoria: 220 NULL → inferência via tipo_nf
  - os_itens.categoria: 8 alias não-padrão → 'Servico'
  - os_itens.sistema: 113 com acento → sem acento
  - ordens_servico.fornecedor: 1 duplo-espaço
  - notas_fiscais.fornecedor: 3 duplo-espaço
  - manutencao_parcelas.fornecedor: 14 duplo-espaço
  - os_itens.servico: 1 duplo-espaço

NÃO altera: numero_os, placa, total_os, data_execucao, fornecedores com "/".
"""
import sys, io, sqlite3, os, shutil, csv, unicodedata
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SCRATCH   = os.path.dirname(os.path.abspath(__file__))
ROOT      = os.path.dirname(SCRATCH)
DB_PATH   = os.path.join(ROOT, "locadora.db")
TS        = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP    = os.path.join(ROOT, f"locadora_backup_{TS}.db")
LOG_PATH  = os.path.join(SCRATCH, f"consolidacao_log_{TS}.csv")
REL_PATH  = os.path.join(SCRATCH, f"relatorio_fase3a2_{TS[:8]}.txt")

BATCH_SIZE = 50

# ── Helpers ────────────────────────────────────────────────────────────────────
relatorio = []
def w(s=""): relatorio.append(s); print(s)

log_rows = []
def log(tabela, reg_id, campo, antes, depois, fonte, regra):
    log_rows.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "tabela": tabela,
        "registro_id": reg_id,
        "campo": campo,
        "valor_antes": antes,
        "valor_depois": depois,
        "fonte": fonte,
        "regra": regra,
    })

def normalize_fornecedor(v):
    if not v:
        return v
    return ' '.join(str(v).split()).upper()

SISTEMA_MAP = {
    'Revisão':    'Revisao',
    'Direção':    'Direcao',
    'Hidráulico': 'Hidraulico',
    'Elétrico':   'Eletrico',
    'Câmbio':     'Cambio',
    'Suspensão':  'Suspensao',
}

CATEGORIA_ALIAS = {
    'MONTAGEM E ALINHAMENTO PNEUS':   'Servico',
    'MONTAGEM E BALANCEAMENTO PNEUS': 'Servico',
    'M.O. PNEUS':                     'Servico',
    'M.O PNEUS':                      'Servico',
    'INSTALAÇÃO E BALANCEAMENTO PNEUS': 'Servico',
    'ALINHAMENTO PNEUS':              'Servico',
    'ALINHAMENTO E CAMBAGEM':         'Servico',
}

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
w("=" * 70)
w("FASE 3A.2 — EXECUÇÃO CONTROLADA DO SANEAMENTO")
w(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
w(f"Banco:  {DB_PATH}")
w("=" * 70)
w()

# ──────────────────────────────────────────────────────────────────────────────
# ETAPA 0 — Backup + Pré-verificação
# ──────────────────────────────────────────────────────────────────────────────
w("ETAPA 0 — BACKUP E PRÉ-VERIFICAÇÃO")
w("-" * 40)

# Backup
shutil.copy2(DB_PATH, BACKUP)
backup_size = os.path.getsize(BACKUP)
w(f"  Backup criado: {os.path.basename(BACKUP)} ({backup_size:,} bytes)")

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA foreign_keys = ON")
cur = conn.cursor()

# Integrity check
cur.execute("PRAGMA integrity_check")
ic = cur.fetchone()[0]
if ic != "ok":
    w(f"  ABORT: PRAGMA integrity_check retornou '{ic}'")
    conn.close()
    sys.exit(1)
w("  PRAGMA integrity_check: OK")

# Snapshot de contagens
MONITORADAS = ["os_itens", "ordens_servico", "notas_fiscais", "manutencao_parcelas"]
contagens_antes = {}
for t in MONITORADAS:
    n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    contagens_antes[t] = n
    w(f"  {t}: {n} registros")
w()

def verificar_contagens():
    for t, antes in contagens_antes.items():
        agora = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        if agora != antes:
            raise RuntimeError(f"CONTAGEM REDUZIDA em {t}: antes={antes}, agora={agora}")

def executar_batch(updates, tabela, campo, fonte, regra):
    """updates: list of (id, valor_antes, valor_depois)"""
    total = 0
    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i:i+BATCH_SIZE]
        try:
            conn.execute("BEGIN")
            for reg_id, antes, depois in batch:
                log(tabela, reg_id, campo, antes, depois, fonte, regra)
                cur.execute(f"UPDATE {tabela} SET {campo} = ? WHERE id = ?", (depois, reg_id))
            verificar_contagens()
            conn.execute("COMMIT")
            total += len(batch)
        except Exception as e:
            conn.execute("ROLLBACK")
            raise RuntimeError(f"ROLLBACK em {tabela}.{campo} batch {i//BATCH_SIZE+1}: {e}")
    return total

# ──────────────────────────────────────────────────────────────────────────────
# ETAPA 1 — os_itens.categoria: 220 NULL → inferência via tipo_nf
# ──────────────────────────────────────────────────────────────────────────────
w("ETAPA 1 — os_itens.categoria: NULL → inferência via notas_fiscais.tipo_nf")
w("-" * 40)

cur.execute("""
    SELECT oi.id,
           (SELECT GROUP_CONCAT(DISTINCT nf.tipo_nf)
            FROM notas_fiscais nf
            WHERE nf.os_id = oi.os_id AND nf.deletado_em IS NULL) AS tipos_nf,
           (SELECT COUNT(DISTINCT nf.id)
            FROM notas_fiscais nf
            WHERE nf.os_id = oi.os_id AND nf.deletado_em IS NULL) AS qtd_nfs
    FROM os_itens oi
    WHERE (oi.categoria IS NULL OR TRIM(oi.categoria) = '')
      AND EXISTS (SELECT 1 FROM ordens_servico os WHERE os.id = oi.os_id AND os.deletado_em IS NULL)
""")
candidatos = cur.fetchall()

updates_cat_inf = []
skipped = []
for item_id, tipos_nf, qtd_nfs in candidatos:
    if not tipos_nf or ',' in tipos_nf:
        skipped.append((item_id, tipos_nf))
        continue
    if tipos_nf == 'Produto':
        updates_cat_inf.append((item_id, None, 'Compra'))
    elif tipos_nf == 'Servico':
        updates_cat_inf.append((item_id, None, 'Servico'))
    else:
        skipped.append((item_id, tipos_nf))

n_compra  = sum(1 for _, __, v in updates_cat_inf if v == 'Compra')
n_servico = sum(1 for _, __, v in updates_cat_inf if v == 'Servico')

total1 = executar_batch(updates_cat_inf, "os_itens", "categoria",
                        "inferencia_tipo_nf", "Regra1_alta_confianca")
w(f"  Updates aplicados: {total1}  (Compra: {n_compra} | Servico: {n_servico})")
w(f"  Ignorados (tipo_nf misto ou ausente): {len(skipped)}")
if skipped:
    for sid, tnf in skipped:
        w(f"    id={sid} tipo_nf={tnf}")
w()

# ──────────────────────────────────────────────────────────────────────────────
# ETAPA 2 — os_itens.categoria: alias não-padrão → 'Servico'
# ──────────────────────────────────────────────────────────────────────────────
w("ETAPA 2 — os_itens.categoria: aliases não-padrão → 'Servico'")
w("-" * 40)

placeholders = ','.join('?' * len(CATEGORIA_ALIAS))
cur.execute(f"SELECT id, categoria FROM os_itens WHERE categoria IN ({placeholders})",
            list(CATEGORIA_ALIAS.keys()))
alias_rows = cur.fetchall()

updates_cat_alias = [(rid, antes, CATEGORIA_ALIAS[antes]) for rid, antes in alias_rows]
total2 = executar_batch(updates_cat_alias, "os_itens", "categoria",
                        "normalizacao_alias", "alias_categoria_pneu")
w(f"  Updates aplicados: {total2}")
for rid, antes, depois in updates_cat_alias:
    w(f"    id={rid}: '{antes}' → '{depois}'")
w()

# ──────────────────────────────────────────────────────────────────────────────
# ETAPA 3 — os_itens.sistema: acentos → sem acento
# ──────────────────────────────────────────────────────────────────────────────
w("ETAPA 3 — os_itens.sistema: normalização de acentos")
w("-" * 40)

placeholders = ','.join('?' * len(SISTEMA_MAP))
cur.execute(f"SELECT id, sistema FROM os_itens WHERE sistema IN ({placeholders})",
            list(SISTEMA_MAP.keys()))
sistema_rows = cur.fetchall()

updates_sis = [(rid, antes, SISTEMA_MAP[antes]) for rid, antes in sistema_rows]
breakdown = {}
for _, antes, _ in updates_sis:
    breakdown[antes] = breakdown.get(antes, 0) + 1

total3 = executar_batch(updates_sis, "os_itens", "sistema",
                        "normalizacao_acento", "sistema_title_case")
w(f"  Updates aplicados: {total3}")
for antes, cnt in sorted(breakdown.items()):
    w(f"    '{antes}' → '{SISTEMA_MAP[antes]}': {cnt}x")
w()

# ──────────────────────────────────────────────────────────────────────────────
# ETAPA 4 — Fornecedores: espaço duplo (3 tabelas)
# ──────────────────────────────────────────────────────────────────────────────
w("ETAPA 4 — Fornecedores: remoção de espaço duplo")
w("-" * 40)

FORN_TABELAS = [
    ("ordens_servico",      "fornecedor"),
    ("notas_fiscais",       "fornecedor"),
    ("manutencao_parcelas", "fornecedor"),
]

total4 = 0
for tabela, campo in FORN_TABELAS:
    cur.execute(f"SELECT id, {campo} FROM {tabela} WHERE {campo} LIKE '%  %'")
    rows = cur.fetchall()
    updates = []
    for rid, val in rows:
        norm = normalize_fornecedor(val)
        if norm != val.strip().upper() if val else False:
            updates.append((rid, val, norm))
        elif val and '  ' in val:
            updates.append((rid, val, norm))

    n = executar_batch(updates, tabela, campo,
                       "normalizacao_espaco", "trim_upper")
    total4 += n
    w(f"  {tabela}.{campo}: {n} updates")
    for rid, antes, depois in updates:
        w(f"    id={rid}: '{antes}' → '{depois}'")
w(f"  Total etapa 4: {total4}")
w()

# ──────────────────────────────────────────────────────────────────────────────
# ETAPA 5 — os_itens.servico: 1 espaço duplo
# ──────────────────────────────────────────────────────────────────────────────
w("ETAPA 5 — os_itens.servico: remoção de espaço duplo")
w("-" * 40)

cur.execute("SELECT id, servico FROM os_itens WHERE servico LIKE '%  %'")
rows5 = cur.fetchall()
updates5 = [(rid, val, ' '.join(val.split())) for rid, val in rows5 if val]

total5 = executar_batch(updates5, "os_itens", "servico",
                        "normalizacao_espaco", "trim_servico")
w(f"  Updates aplicados: {total5}")
for rid, antes, depois in updates5:
    w(f"    id={rid}: '{antes}' → '{depois}'")
w()

# ──────────────────────────────────────────────────────────────────────────────
# ETAPA 6 — Pós-verificação
# ──────────────────────────────────────────────────────────────────────────────
w("ETAPA 6 — PÓS-VERIFICAÇÃO")
w("-" * 40)
erros_pos = []

# Contagens intactas
for t, antes in contagens_antes.items():
    agora = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    status = "✓" if agora == antes else "✗ ERRO"
    w(f"  {t}: antes={antes}, agora={agora} {status}")
    if agora != antes:
        erros_pos.append(f"Contagem alterada em {t}")

# FK check
cur.execute("PRAGMA foreign_key_check")
fk_erros = cur.fetchall()
w(f"  FK violations: {len(fk_erros)} {'✓' if not fk_erros else '✗'}")
if fk_erros:
    for fe in fk_erros:
        erros_pos.append(f"FK violation: {fe}")

# os_itens.categoria NULL
n_cat_null = cur.execute("SELECT COUNT(*) FROM os_itens WHERE categoria IS NULL OR TRIM(categoria) = ''").fetchone()[0]
w(f"  os_itens com categoria NULL restantes: {n_cat_null} {'✓' if n_cat_null == 0 else '⚠ (esperado 0)'}")

# os_itens.sistema com acento
n_sis_acento = cur.execute(
    "SELECT COUNT(*) FROM os_itens WHERE sistema IN ('Revisão','Direção','Elétrico','Câmbio','Hidráulico','Suspensão')"
).fetchone()[0]
w(f"  os_itens.sistema com acento restantes: {n_sis_acento} {'✓' if n_sis_acento == 0 else '⚠'}")

# OS-2026-0180 intacta
data_0180 = cur.execute("SELECT data_execucao FROM ordens_servico WHERE numero_os = 'OS-2026-0180'").fetchone()
data_0180_val = data_0180[0] if data_0180 else "(não encontrada)"
w(f"  OS-2026-0180.data_execucao: {data_0180_val} {'✓ (intacta)' if data_0180_val == '2026-03-10' else '⚠'}")

# Fornecedores duplo espaço
for tabela, campo in FORN_TABELAS:
    n = cur.execute(f"SELECT COUNT(*) FROM {tabela} WHERE {campo} LIKE '%  %'").fetchone()[0]
    w(f"  {tabela}.{campo} com duplo espaço restantes: {n} {'✓' if n == 0 else '⚠'}")

w()
if erros_pos:
    w("⚠ ATENÇÃO: Erros detectados na pós-verificação:")
    for e in erros_pos:
        w(f"  - {e}")
else:
    w("✓ Pós-verificação concluída sem erros.")

conn.close()

# ──────────────────────────────────────────────────────────────────────────────
# SALVAR LOG CSV
# ──────────────────────────────────────────────────────────────────────────────
with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["timestamp","tabela","registro_id","campo",
                                            "valor_antes","valor_depois","fonte","regra"])
    writer.writeheader()
    writer.writerows(log_rows)

# ──────────────────────────────────────────────────────────────────────────────
# RELATÓRIO FINAL
# ──────────────────────────────────────────────────────────────────────────────
total_geral = total1 + total2 + total3 + total4 + total5
w()
w("=" * 70)
w("RELATÓRIO FINAL")
w("=" * 70)
w(f"  Backup:                 {os.path.basename(BACKUP)}")
w(f"  Log de auditoria:       {os.path.basename(LOG_PATH)} ({len(log_rows)} registros)")
w()
w(f"  Etapa 1 (cat. inferência):  {total1} updates")
w(f"  Etapa 2 (cat. alias):       {total2} updates")
w(f"  Etapa 3 (sistema acento):   {total3} updates")
w(f"  Etapa 4 (fornec. espaço):   {total4} updates")
w(f"  Etapa 5 (servico espaço):   {total5} updates")
w(f"  TOTAL:                      {total_geral} updates")
w()
w("  Ignorados (reservados para revisão humana):")
w("    OS-2026-0180: data_execucao divergente → NÃO alterado")
w("    31 OS com '/': fornecedor multi-fornecedor → NÃO alterado")
w(f"    {len(skipped)} itens sem tipo_nf definido → NÃO alterados")
w()
w(f"  Status: {'OK — sem erros' if not erros_pos else 'COM ERROS — verificar acima'}")
w(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
w("=" * 70)

# Salvar relatório
with open(REL_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(relatorio))

print(f"\nRelatório salvo em: {REL_PATH}", file=sys.stderr)
print(f"Log CSV salvo em:   {LOG_PATH}", file=sys.stderr)
