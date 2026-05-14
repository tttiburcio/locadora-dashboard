"""
Script de validação: verifica se OS-2025-0026 é detectada como substituída
após a correção do algoritmo de inferência de posicao_pneu.
"""
import sys
sys.path.insert(0, r'c:\Users\ADM\Documents\locadora-dashboard\backend')

import requests

BASE = "http://localhost:8000"

resp = requests.get(f"{BASE}/api/maintenance_analysis/intervalos", params={"sistema": "Pneu"}, timeout=30)
if resp.status_code != 200:
    print(f"ERRO HTTP {resp.status_code}: {resp.text[:500]}")
    sys.exit(1)

data = resp.json()
por_placa = data.get("por_placa", [])

# Localizar MAX4116
max4116 = next((p for p in por_placa if p["placa"] == "MAX4116"), None)
if not max4116:
    print("MAX4116 não encontrado na resposta")
    sys.exit(1)

print(f"MAX4116 — {max4116['n_eventos']} eventos, km_atual={max4116.get('km_atual')}")
print(f"  km_por_posicao: {max4116.get('km_por_posicao')}")
print()

for medida in max4116.get("por_medida", []):
    print(f"  Espec: {medida['espec']} | {medida['n_eventos']} conjuntos")
    for conj in medida.get("conjuntos", []):
        last_fase = conj["fases"][-1]
        status = "EM USO" if last_fase.get("em_uso") else "SUBSTITUÍDO"
        descartado = conj.get("descartado", False)
        marca = conj.get("marca", "?")
        os_ref = conj.get("os_ref", "?")
        km_compra = conj.get("km_compra", "?")
        pos_atual = last_fase.get("posicao", "?")
        qtd = conj.get("qtd", "?")
        print(f"    [{status}] {os_ref} | {marca} | km={km_compra} | pos={pos_atual} | qtd={qtd} | descartado={descartado}")

print()
# Verificação automática
conjs_traseiro_17525 = [
    conj
    for medida in max4116.get("por_medida", [])
    if "17.5" in str(medida.get("espec", ""))
    for conj in medida.get("conjuntos", [])
]

os_2025 = next((c for c in conjs_traseiro_17525 if "2025-0026" in str(c.get("os_ref", ""))), None)
os_2026 = next((c for c in conjs_traseiro_17525 if "2026-0217" in str(c.get("os_ref", ""))), None)

print("=== RESULTADO DA VALIDAÇÃO ===")
if os_2025:
    fase_final = os_2025["fases"][-1]
    em_uso = fase_final.get("em_uso", True)
    desc = os_2025.get("descartado", False)
    print(f"OS-2025-0026 (SUPERLAND): em_uso={em_uso} | descartado={desc}")
    if not em_uso and desc:
        print("  ✅ CORRETO — pneu marcado como substituído!")
    else:
        print("  ❌ BUG AINDA PRESENTE — pneu ainda marcado como em uso")
else:
    print("OS-2025-0026 não encontrada nos conjuntos")

if os_2026:
    fase_final = os_2026["fases"][-1]
    em_uso = fase_final.get("em_uso", False)
    print(f"OS-2026-0217 (MAVERLOUS): em_uso={em_uso}")
    if em_uso:
        print("  ✅ CORRETO — pneu novo marcado como em uso!")
    else:
        print("  ❌ PROBLEMA — pneu novo deveria estar em uso")
else:
    print("OS-2026-0217 não encontrada nos conjuntos")
