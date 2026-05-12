"""
FASE 3A.1 — Script Master: Orquestra todos os dry-runs e consolida relatório.
Nenhum UPDATE/INSERT/DELETE é executado em nenhum sub-script.
Output: scratch/dryrun_relatorio_completo.txt
"""
import sys, io, os, subprocess
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SCRATCH = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(SCRATCH, "dryrun_relatorio_completo.txt")

SCRIPTS = [
    ("Script 1 — Inferência de Categoria",  "fase3a1_categoria_inferencia.py",  "dryrun_categoria.txt"),
    ("Script 2 — Normalização Textual",     "fase3a1_normalizacao_textual.py",  "dryrun_normalizacao.txt"),
    ("Script 3 — Match de Fornecedores",    "fase3a1_fornecedores_match.py",    "dryrun_fornecedores.txt"),
    ("Script 4 — Catálogo de Serviços",     "fase3a1_servicos_catalogo.py",     "dryrun_servicos.txt"),
    ("Script 5 — Conflitos SQL vs Excel",   "fase3a1_conflitos_excel_sql.py",   "dryrun_conflitos.txt"),
    ("Script 6 — Impacto em Produção",      "fase3a1_impacto_producao.py",      "dryrun_impacto.txt"),
]

print("=" * 70)
print("FASE 3A.1 — EXECUÇÃO MASTER DRY-RUN")
print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("NENHUM UPDATE SERÁ EXECUTADO EM NENHUM SUB-SCRIPT.")
print("=" * 70)
print()

erros = []

for label, script, output_file in SCRIPTS:
    script_path = os.path.join(SCRATCH, script)
    output_path = os.path.join(SCRATCH, output_file)
    print(f"Executando: {label} ...", end=" ", flush=True)

    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=SCRATCH,
    )

    if result.returncode != 0:
        print(f"ERRO (código {result.returncode})")
        erros.append((label, result.stderr))
    else:
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"OK ({size:,} bytes) → {output_file}")
        else:
            print("OK (sem arquivo de saída gerado)")

print()

# ── Consolidar relatório ───────────────────────────────────────────────────────
print("Consolidando relatório completo...", end=" ", flush=True)

with open(OUT_PATH, "w", encoding="utf-8") as out:
    out.write("=" * 80 + "\n")
    out.write("RELATÓRIO COMPLETO DRY-RUN — FASE 3A.1\n")
    out.write(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    out.write("NENHUMA ALTERAÇÃO FOI FEITA NO BANCO OU NO EXCEL.\n")
    out.write("=" * 80 + "\n\n")

    for label, script, output_file in SCRIPTS:
        output_path = os.path.join(SCRATCH, output_file)
        out.write("\n" + "#" * 80 + "\n")
        out.write(f"# {label.upper()}\n")
        out.write(f"# Arquivo: {output_file}\n")
        out.write("#" * 80 + "\n\n")
        if os.path.exists(output_path):
            with open(output_path, "r", encoding="utf-8", errors="replace") as f:
                out.write(f.read())
        else:
            out.write(f"  [ARQUIVO NÃO GERADO — verificar erros]\n")
        out.write("\n")

    # ── Seção de sumário de aprovação ────────────────────────────────────────
    out.write("\n" + "=" * 80 + "\n")
    out.write("APROVAÇÃO NECESSÁRIA ANTES DA FASE 3A.2\n")
    out.write("=" * 80 + "\n\n")
    out.write("Itens que EXIGEM revisão humana antes de qualquer escrita no banco:\n\n")
    out.write("  1. OS-2026-0180 — data_execucao divergente (ver dryrun_conflitos.txt)\n")
    out.write("  2. Itens de categoria AMBÍGUO e IMPOSSÍVEL (ver dryrun_categoria.txt)\n")
    out.write("  3. Grupos de fornecedores com alias MÉDIA confiança (ver dryrun_fornecedores.txt)\n")
    out.write("  4. Fornecedores com '/' — decidir: 1 vínculo ou múltiplos (ver dryrun_fornecedores.txt)\n")
    out.write("  5. Serviços AMBÍGUOS sem grupo identificado (ver dryrun_servicos.txt)\n")
    out.write("\n")
    out.write("Itens APROVADOS para execução automática na Fase 3A.2:\n\n")
    out.write("  A. Inferências de categoria com confiança >= 85% (ver dryrun_categoria.txt)\n")
    out.write("  B. Normalizações sem colisão [OK] (ver dryrun_normalizacao.txt)\n")
    out.write("  C. Remoção de fallback Excel de reembolsos/faturamento no backend (ver dryrun_impacto.txt)\n")
    out.write("\n")
    out.write("ASSINATURA DE APROVAÇÃO (preencher manualmente):\n")
    out.write("  Revisado por: ___________________________\n")
    out.write(f"  Data:         {datetime.now().strftime('%Y-%m-%d')}\n")
    out.write("  Aprovado:     [ ] SIM    [ ] NÃO — motivo: ___________\n")

size = os.path.getsize(OUT_PATH)
print(f"OK ({size:,} bytes)")
print()

# ── Resultado final ────────────────────────────────────────────────────────────
print("=" * 70)
if erros:
    print(f"CONCLUÍDO COM {len(erros)} ERRO(S):")
    for label, stderr in erros:
        print(f"\n  {label}:")
        for linha in stderr.strip().splitlines()[-5:]:
            print(f"    {linha}")
else:
    print("TODOS OS SCRIPTS CONCLUÍDOS SEM ERRO.")
print()
print(f"Arquivos gerados em {SCRATCH}/:")
for _, _, f in SCRIPTS:
    p = os.path.join(SCRATCH, f)
    if os.path.exists(p):
        print(f"  ✓ {f} ({os.path.getsize(p):,} bytes)")
    else:
        print(f"  ✗ {f} (NÃO GERADO)")
print(f"  ✓ dryrun_relatorio_completo.txt ({size:,} bytes)")
print()
print("Próximo passo: revisar relatórios acima e aprovar Fase 3A.2.")
print("=" * 70)
