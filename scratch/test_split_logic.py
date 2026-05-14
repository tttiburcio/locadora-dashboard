import copy
from collections import defaultdict

def _pos_parts(p: str) -> list:
    return [x.strip() for x in (p or "").split("+") if x.strip()]

# Mock data structure simulating the bug state
mock_all_conjs = [
    {
        "os_ref": "OS-2025-0112", "marca": "CONTINENTAL", "qtd": 2,
        "fases": [{"posicao": "DIANTEIRO", "km_inicio": 55000, "data_inicio": "2025-09-24", "em_uso": True}]
    },
    {
        "os_ref": "OS-2026-0216", "marca": "GOODYEAR", "qtd": 1,
        "fases": [{"posicao": "DIANTEIRO", "km_inicio": 64895, "data_inicio": "2026-01-16", "em_uso": True}]
    }
]

def run_replacement_logic(conjs_flat):
    # 1. Tokenization
    all_tokens = []
    for conj in conjs_flat:
        last_f = conj["fases"][-1]
        pos = last_f.get("posicao")
        if not pos: continue
        qtd = max(1, int(conj.get("qtd") or 1))
        for i in range(qtd):
            for pp in (_pos_parts(pos) or [pos]):
                all_tokens.append({
                    "conj": conj,
                    "pos": pp,
                    "idx": i,
                    "km": last_f["km_inicio"] or 0,
                    "dt": last_f.get("data_inicio") or "",
                    "replaced_by": None
                })
    all_tokens.sort(key=lambda t: (t["km"], t["dt"] or ""))
    
    # 2. Stateful replacement match
    active_tokens_by_pos = {}
    for token in all_tokens:
        p = token["pos"]
        pool = active_tokens_by_pos.setdefault(p, [])
        if pool:
             victim = pool.pop(0) # replace oldest
             victim["replaced_by"] = token
        pool.append(token)
        
    # 3. Remapping & Splitting
    conj_to_tokens = defaultdict(list)
    for t in all_tokens:
        conj_to_tokens[id(t["conj"])].append(t)
        
    output_list = []
    for orig_conj in conjs_flat:
        tokens = conj_to_tokens.get(id(orig_conj), [])
        if not tokens:
            output_list.append(orig_conj)
            continue
        
        # group tokens of THIS original row by their specific replacement fate
        by_fate = defaultdict(list)
        for t in tokens:
            rid = id(t["replaced_by"]["conj"]) if t["replaced_by"] else None
            by_fate[rid].append(t)
            
        for rid, t_sublist in by_fate.items():
            sc = copy.deepcopy(orig_conj)
            sc["qtd"] = len(t_sublist) # partial size!
            
            last_f = sc["fases"][-1]
            rep = t_sublist[0]["replaced_by"]
            if rep:
                 sc["descartado"] = True
                 last_f["em_uso"] = False
                 last_f["km_fim"] = rep["km"]
                 last_f["data_fim"] = rep["dt"]
                 last_f["descartado"] = True
            else:
                 sc["descartado"] = False
                 last_f["em_uso"] = True
                 
            output_list.append(sc)
            
    return output_list

results = run_replacement_logic(mock_all_conjs)

print("FINAL CALCULATED SETS:")
for c in results:
    st = "DISCARDED" if c.get("descartado") else "IN-USE"
    print(f"  - {c['marca']} (Qtd={c['qtd']}) -> {st} via OS={c.get('os_ref')}")

assert len(results) == 3, f"Should produce 3 objects, got {len(results)}"
