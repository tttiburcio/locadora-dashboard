from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from pathlib import Path

app = FastAPI(title="TKJ Locadora API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EXCEL_PATH = Path(__file__).parent.parent / "Locadora.xlsx"

SHEETS = {
    "frota":         "🚛 FROTA",
    "fat_unitario":  "💰 FAT_UNITARIO",
    "reembolsos":    "↩️ REEMBOLSOS",
    "manutencoes":   "🔧 MANUTENCOES",
    "faturamento":   "🧾 FATURAMENTO",
    "seguro_mensal": "📋 SEGURO_MENSAL",
    "impostos":      "📋 IMPOSTOS",
    "rastreamento":  "📍RASTREAMENTO",
    "contratos":     "📄 CONTRATOS",
    "clientes":      "🏢 CLIENTES",
}

_cache: dict = {}


def load_raw() -> dict:
    if not _cache:
        xl = pd.ExcelFile(EXCEL_PATH)
        for key, name in SHEETS.items():
            try:
                _cache[key] = xl.parse(name)
            except Exception as e:
                print(f"Warning: sheet '{name}' not found: {e}")
                _cache[key] = pd.DataFrame()
    return _cache


def safe(v):
    try:
        f = float(v)
        return 0.0 if (np.isnan(f) or np.isinf(f)) else round(f, 2)
    except Exception:
        return 0.0


def _parse(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if not df.empty and col in df.columns:
        df = df.copy()
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def _filter_year(df: pd.DataFrame, col: str, year: int) -> pd.DataFrame:
    if df.empty or col not in df.columns:
        return df
    return df[df[col].dt.year == year].copy()


MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _dedup_manut(manut_raw: pd.DataFrame) -> pd.DataFrame:
    if not manut_raw.empty and "IDOrdServ" in manut_raw.columns:
        com_os = manut_raw.dropna(subset=["IDOrdServ"]).drop_duplicates(subset=["IDOrdServ"])
        sem_os = manut_raw[manut_raw["IDOrdServ"].isna()]
        return pd.concat([com_os, sem_os], ignore_index=True)
    return manut_raw.copy()


def compute(year: int):
    data = load_raw()

    frota  = data["frota"].copy()
    fat    = _filter_year(_parse(data["fat_unitario"].copy(),  "Mes"),          "Mes",          year)
    reimb  = _filter_year(_parse(data["reembolsos"].copy(),   "Emissão"),       "Emissão",      year)
    fat_sh = _filter_year(_parse(data["faturamento"].copy(),  "Emissão"),       "Emissão",      year)
    seg    = _filter_year(_parse(data["seguro_mensal"].copy(), "Vencimento"),    "Vencimento",   year)
    rast   = _filter_year(_parse(data["rastreamento"].copy(),  "Vencimento"),    "Vencimento",   year)

    imp = data["impostos"].copy()
    if not imp.empty and "AnoImposto" in imp.columns:
        imp = imp[imp["AnoImposto"] == year].copy()

    manut_raw = _filter_year(_parse(data["manutencoes"].copy(), "DataExecução"), "DataExecução", year)
    manut     = _dedup_manut(manut_raw)

    # ── Receitas por veículo ─────────────────────────────────
    rev_loc  = fat.groupby("IDVeiculo")["Medicao"].sum().rename("ReceitaLocacao") if not fat.empty else pd.Series(dtype=float, name="ReceitaLocacao")
    rev_reib = (reimb.dropna(subset=["IDVeiculo"]).groupby("IDVeiculo")["ValorReembolso"].sum().rename("ReceitaReembolso")
                if not reimb.empty else pd.Series(dtype=float, name="ReceitaReembolso"))

    # ── Custos por veículo ───────────────────────────────────
    c_manut = (manut.dropna(subset=["IDVeiculo"]).groupby("IDVeiculo")["TotalOS"].sum().rename("CustoManutencao")
               if not manut.empty else pd.Series(dtype=float, name="CustoManutencao"))
    c_seg   = (seg.groupby("IDVeiculo")["Valor"].sum().rename("CustoSeguro")
               if not seg.empty else pd.Series(dtype=float, name="CustoSeguro"))
    c_rast  = (rast.groupby("IDVeiculo")["Valor"].sum().rename("CustoRastreamento")
               if not rast.empty else pd.Series(dtype=float, name="CustoRastreamento"))

    if not imp.empty and "IDVeiculo" in imp.columns:
        val_col = "ValorTotalFinal" if "ValorTotalFinal" in imp.columns else None
        if val_col is None:
            imp["_val"] = imp.get("ValorIpva", 0).fillna(0) + imp.get("ValorLicenc", 0).fillna(0)
            val_col = "_val"
        c_imp = imp.groupby("IDVeiculo")[val_col].sum().rename("CustoImpostos")
    else:
        c_imp = pd.Series(dtype=float, name="CustoImpostos")

    # ── Dias trabalhados / parados ───────────────────────────
    if not fat.empty and "Trabalhado" in fat.columns:
        dias = fat.groupby("IDVeiculo").agg(Trabalhado=("Trabalhado", "sum"), Parado=("Parado", "sum"))
    else:
        dias = pd.DataFrame(columns=["Trabalhado", "Parado"])

    # ── Contrato principal por veículo (mais recente) ────────
    contrato_info = pd.DataFrame(columns=["IDVeiculo", "Contrato", "CidadeOp"])
    if not fat.empty and "Contrato" in fat.columns:
        contrato_info = (fat.dropna(subset=["IDVeiculo", "Contrato"])
                         .groupby("IDVeiculo")["Contrato"]
                         .agg(lambda x: x.value_counts().index[0] if len(x) > 0 else "—")
                         .rename("Contrato")
                         .reset_index())

    # ── Consolidar na frota ──────────────────────────────────
    base_cols = ["IDVeiculo", "Placa", "Marca", "Modelo", "Status", "Tipagem", "Implemento"]
    base_cols = [c for c in base_cols if c in frota.columns]
    if "ValorTotal" in frota.columns:
        base_cols.append("ValorTotal")

    df = (
        frota[base_cols]
        .set_index("IDVeiculo")
        .join(rev_loc,  how="left")
        .join(rev_reib, how="left")
        .join(c_manut,  how="left")
        .join(c_seg,    how="left")
        .join(c_imp,    how="left")
        .join(c_rast,   how="left")
        .join(dias,     how="left")
        .fillna(0)
        .reset_index()
    )

    if not contrato_info.empty:
        df = df.merge(contrato_info, on="IDVeiculo", how="left")
        df["Contrato"] = df["Contrato"].fillna("—")
    else:
        df["Contrato"] = "—"

    df["ReceitaTotal"] = df["ReceitaLocacao"] + df["ReceitaReembolso"]
    df["CustoTotal"]   = df["CustoManutencao"] + df["CustoSeguro"] + df["CustoImpostos"] + df["CustoRastreamento"]
    df["Margem"]       = df["ReceitaTotal"] - df["CustoTotal"]
    df["MargemPct"]    = np.where(df["ReceitaTotal"] > 0, df["Margem"] / df["ReceitaTotal"] * 100, 0)
    df["ReceitaPorDia"]= np.where(df["Trabalhado"] > 0, df["ReceitaTotal"] / df["Trabalhado"], 0)
    df["CustoPorDia"]  = np.where(df["Trabalhado"] > 0, df["CustoTotal"]  / df["Trabalhado"], 0)
    df["MargemPorDia"] = np.where(df["Trabalhado"] > 0, df["Margem"]       / df["Trabalhado"], 0)
    df["ROI"] = np.where(df.get("ValorTotal", pd.Series(0, index=df.index)) > 0,
                         df["Margem"] / df.get("ValorTotal", pd.Series(1, index=df.index)) * 100, 0) if "ValorTotal" in df.columns else 0

    df_active = df[(df["ReceitaTotal"] > 0) | (df["CustoTotal"] > 0)].copy()

    # ── Evolução mensal ──────────────────────────────────────
    def monthly_group(frame, date_col, val_col, out_col):
        if frame.empty or date_col not in frame.columns:
            return pd.DataFrame({"Mes": range(1, 13), out_col: 0.0})
        grp = frame.assign(_m=frame[date_col].dt.month).groupby("_m")[val_col].sum().reset_index()
        grp.columns = ["Mes", out_col]
        base = pd.DataFrame({"Mes": range(1, 13)})
        return base.merge(grp, on="Mes", how="left").fillna(0)

    frota_ids     = set(frota["IDVeiculo"].dropna().tolist())
    manut_frota   = (manut[manut["IDVeiculo"].isin(frota_ids)].dropna(subset=["IDVeiculo"])
                     if not manut.empty else manut)

    ml   = monthly_group(fat,         "Mes",          "Medicao",        "Locacao")
    mr   = monthly_group(reimb,       "Emissão",       "ValorReembolso", "Reembolso")
    mcm  = monthly_group(manut_frota, "DataExecução",  "TotalOS",        "CustoManutencao")
    mcs  = monthly_group(seg,         "Vencimento",    "Valor",          "CustoSeguro")
    mcr  = monthly_group(rast,        "Vencimento",    "Valor",          "CustoRastreamento")

    monthly = (ml.merge(mr, on="Mes").merge(mcm, on="Mes").merge(mcs, on="Mes").merge(mcr, on="Mes"))
    monthly["ReceitaTotal"] = monthly["Locacao"] + monthly["Reembolso"]
    monthly["CustoTotal"]   = monthly["CustoManutencao"] + monthly["CustoSeguro"] + monthly["CustoRastreamento"]
    monthly["Margem"]       = monthly["ReceitaTotal"] - monthly["CustoTotal"]
    monthly["MesLabel"]     = monthly["Mes"].apply(lambda m: MESES_PT[m - 1])

    # ── KPIs ─────────────────────────────────────────────────
    faturado   = safe(fat_sh["ValorLocacoes"].sum()) if not fat_sh.empty and "ValorLocacoes" in fat_sh.columns else 0.0
    recebido   = safe(fat_sh["ValorRecebido"].sum()) if not fat_sh.empty and "ValorRecebido" in fat_sh.columns else 0.0
    reembolsos = safe(reimb["ValorReembolso"].sum()) if not reimb.empty and "ValorReembolso" in reimb.columns else 0.0

    receita_total   = safe(df_active["ReceitaTotal"].sum())
    custo_total     = safe(df_active["CustoTotal"].sum())
    margem          = safe(df_active["Margem"].sum())
    margem_pct      = round(margem / receita_total * 100, 1) if receita_total > 0 else 0.0
    veiculos_ativos = int(len(df_active))
    veiculos_lucr   = int((df_active["Margem"] > 0).sum())

    taxa_util = 0.0
    if not fat.empty and "Trabalhado" in fat.columns and "Parado" in fat.columns:
        t = fat["Trabalhado"].sum(); p = fat["Parado"].sum()
        if (t + p) > 0:
            taxa_util = round(t / (t + p) * 100, 1)

    best_v = worst_v = None
    if not df_active.empty:
        bi = df_active["Margem"].idxmax()
        wi = df_active["Margem"].idxmin()
        best_v  = {"placa": str(df_active.loc[bi, "Placa"]), "modelo": str(df_active.loc[bi, "Modelo"]), "margem": safe(df_active.loc[bi, "Margem"])}
        worst_v = {"placa": str(df_active.loc[wi, "Placa"]), "modelo": str(df_active.loc[wi, "Modelo"]), "margem": safe(df_active.loc[wi, "Margem"])}

    kpis = {
        "veiculos_ativos":      veiculos_ativos,
        "veiculos_total":       int(len(frota)),
        "veiculos_lucrativos":  veiculos_lucr,
        "veiculos_deficitarios": veiculos_ativos - veiculos_lucr,
        "faturado":             faturado,
        "recebido":             recebido,
        "receita_locacao":      safe(df_active["ReceitaLocacao"].sum()),
        "receita_reembolso":    reembolsos,
        "receita_total":        receita_total,
        "custo_manutencao":     safe(df_active["CustoManutencao"].sum()),
        "custo_seguro":         safe(df_active["CustoSeguro"].sum()),
        "custo_impostos":       safe(df_active["CustoImpostos"].sum()),
        "custo_rastreamento":   safe(df_active["CustoRastreamento"].sum()),
        "custo_total":          custo_total,
        "margem":               margem,
        "margem_pct":           margem_pct,
        "taxa_utilizacao":      taxa_util,
        "melhor_veiculo":       best_v,
        "pior_veiculo":         worst_v,
        "receita_por_veiculo":  round(receita_total / veiculos_ativos, 2) if veiculos_ativos else 0.0,
        "margem_por_veiculo":   round(margem / veiculos_ativos, 2) if veiculos_ativos else 0.0,
        "custo_sobre_receita":  round(custo_total / receita_total * 100, 1) if receita_total > 0 else 0.0,
        "inconsistencias":      _check_inconsistencias(df_active, year),
    }

    return df_active, monthly, kpis, fat, reimb, manut, seg, rast, imp


def _check_inconsistencias(df_active, year):
    issues = []
    if df_active.empty:
        return issues
    sold = df_active[df_active["Status"].str.upper().str.contains("VEND", na=False)]
    for _, row in sold.iterrows():
        issues.append({
            "tipo": "vendido_com_movimento",
            "placa": str(row["Placa"]),
            "descricao": (
                f"{row['Placa']} ({row.get('Modelo','')}) consta como vendido "
                f"mas possui lançamentos em {year} "
                f"(receita {safe(row['ReceitaTotal']):.2f} / custo {safe(row['CustoTotal']):.2f})"
            ),
        })
    return issues


def _linear_projection(monthly_data: list, n_future: int = 4) -> list:
    """Simple linear regression projection on non-zero months."""
    pts = [(i + 1, v) for i, v in enumerate(monthly_data) if v > 0]
    if len(pts) < 2:
        return []
    xs = np.array([p[0] for p in pts])
    ys = np.array([p[1] for p in pts])
    coeffs = np.polyfit(xs, ys, 1)
    slope, intercept = coeffs
    resid  = ys - np.polyval(coeffs, xs)
    std    = float(np.std(resid))
    last_x = int(xs[-1])
    proj   = []
    for i in range(1, n_future + 1):
        x   = last_x + i
        val = float(np.polyval(coeffs, x))
        proj.append({
            "x": x,
            "projected": max(0.0, round(val, 2)),
            "low":       max(0.0, round(val - std, 2)),
            "high":      max(0.0, round(val + std, 2)),
        })
    return proj


# ─────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────

@app.get("/api/years")
def get_years():
    data = load_raw()
    years: set = set()
    fat = _parse(data["fat_unitario"], "Mes")
    if "Mes" in fat.columns:
        years.update(fat["Mes"].dropna().dt.year.astype(int).tolist())
    fsh = _parse(data["faturamento"], "Emissão")
    if "Emissão" in fsh.columns:
        years.update(fsh["Emissão"].dropna().dt.year.astype(int).tolist())
    return {"years": sorted(years, reverse=True)}


@app.get("/api/kpis")
def get_kpis(year: int = Query(...)):
    _, _, kpis, *_ = compute(year)
    return kpis


@app.get("/api/monthly")
def get_monthly(year: int = Query(...)):
    _, monthly, *_ = compute(year)
    records = []
    for _, row in monthly.iterrows():
        records.append({k: safe(v) if isinstance(v, (float, int, np.floating)) else str(v) for k, v in row.items()})
    return {"monthly": records}


@app.get("/api/vehicles")
def get_vehicles(year: int = Query(...), region: str = Query(None)):
    df, _, _, fat, *_ = compute(year)

    # Optional region/contract filter
    if region and not fat.empty and "Contrato" in fat.columns:
        ids_region = set(fat[fat["Contrato"] == region]["IDVeiculo"].dropna().astype(int).tolist())
        df = df[df["IDVeiculo"].isin(ids_region)]

    vehicles = []
    for rank, (_, row) in enumerate(df.sort_values("Margem", ascending=False).iterrows(), 1):
        vehicles.append({
            "rank":               rank,
            "id":                 int(row.get("IDVeiculo", 0)),
            "placa":              str(row.get("Placa", "")),
            "marca":              str(row.get("Marca", "")),
            "modelo":             str(row.get("Modelo", "")),
            "tipagem":            str(row.get("Tipagem", "")),
            "implemento":         str(row.get("Implemento", "")),
            "status":             str(row.get("Status", "")),
            "contrato":           str(row.get("Contrato", "—")),
            "valor_total":        safe(row.get("ValorTotal", 0)),
            "receita_locacao":    safe(row["ReceitaLocacao"]),
            "receita_reembolso":  safe(row["ReceitaReembolso"]),
            "receita_total":      safe(row["ReceitaTotal"]),
            "custo_manutencao":   safe(row["CustoManutencao"]),
            "custo_seguro":       safe(row["CustoSeguro"]),
            "custo_impostos":     safe(row["CustoImpostos"]),
            "custo_rastreamento": safe(row["CustoRastreamento"]),
            "custo_total":        safe(row["CustoTotal"]),
            "margem":             safe(row["Margem"]),
            "margem_pct":         safe(row["MargemPct"]),
            "dias_trabalhado":    safe(row["Trabalhado"]),
            "dias_parado":        safe(row["Parado"]),
            "receita_por_dia":    safe(row["ReceitaPorDia"]),
            "custo_por_dia":      safe(row["CustoPorDia"]),
            "margem_por_dia":     safe(row["MargemPorDia"]),
            "roi":                safe(row.get("ROI", 0)),
        })
    return {"vehicles": vehicles}


@app.get("/api/regions")
def get_regions(year: int = Query(...)):
    data  = load_raw()
    fat   = _filter_year(_parse(data["fat_unitario"].copy(), "Mes"), "Mes", year)
    if fat.empty or "Contrato" not in fat.columns:
        return {"regions": []}
    regions = sorted(fat["Contrato"].dropna().unique().tolist())
    return {"regions": regions}


@app.get("/api/vehicle/{placa}")
def get_vehicle(placa: str, year: int = Query(...)):
    df, _, _, fat, reimb, manut, seg, rast, _ = compute(year)

    mask = df["Placa"] == placa
    if not mask.any():
        return {"error": "Vehicle not found"}

    row  = df[mask].iloc[0]
    id_v = row["IDVeiculo"]

    info = {
        "placa":      str(row["Placa"]),
        "marca":      str(row["Marca"]),
        "modelo":     str(row["Modelo"]),
        "tipagem":    str(row.get("Tipagem", "")),
        "implemento": str(row.get("Implemento", "")),
        "status":     str(row["Status"]),
        "contrato":   str(row.get("Contrato", "—")),
        "valor_total": safe(row.get("ValorTotal", 0)),
    }

    kpis_v = {
        "receita_locacao":    safe(row["ReceitaLocacao"]),
        "receita_reembolso":  safe(row["ReceitaReembolso"]),
        "receita_total":      safe(row["ReceitaTotal"]),
        "custo_manutencao":   safe(row["CustoManutencao"]),
        "custo_seguro":       safe(row["CustoSeguro"]),
        "custo_impostos":     safe(row["CustoImpostos"]),
        "custo_rastreamento": safe(row["CustoRastreamento"]),
        "custo_total":        safe(row["CustoTotal"]),
        "margem":             safe(row["Margem"]),
        "margem_pct":         safe(row["MargemPct"]),
        "dias_trabalhado":    safe(row["Trabalhado"]),
        "dias_parado":        safe(row["Parado"]),
        "receita_por_dia":    safe(row["ReceitaPorDia"]),
        "custo_por_dia":      safe(row["CustoPorDia"]),
        "margem_por_dia":     safe(row["MargemPorDia"]),
        "roi":                safe(row.get("ROI", 0)),
    }

    def vf(df_s, id_col="IDVeiculo"):
        if df_s.empty or id_col not in df_s.columns:
            return df_s
        return df_s[df_s[id_col] == id_v]

    fat_v   = vf(fat)
    reimb_v = vf(reimb)
    manut_v = vf(manut)
    seg_v   = vf(seg)
    rast_v  = vf(rast)

    # Monthly breakdown
    monthly = []
    for m in range(1, 13):
        mr = {"month": m, "monthName": MESES_PT[m - 1]}
        mr["receita_locacao"]    = safe(fat_v[fat_v["Mes"].dt.month == m]["Medicao"].sum()) if not fat_v.empty and "Mes" in fat_v.columns else 0.0
        mr["receita_reembolso"]  = safe(reimb_v[reimb_v["Emissão"].dt.month == m]["ValorReembolso"].sum()) if not reimb_v.empty and "Emissão" in reimb_v.columns else 0.0
        mr["receita_total"]      = mr["receita_locacao"] + mr["receita_reembolso"]
        mr["custo_manutencao"]   = safe(manut_v[manut_v["DataExecução"].dt.month == m]["TotalOS"].sum()) if not manut_v.empty and "DataExecução" in manut_v.columns else 0.0
        mr["custo_seguro"]       = safe(seg_v[seg_v["Vencimento"].dt.month == m]["Valor"].sum()) if not seg_v.empty and "Vencimento" in seg_v.columns else 0.0
        mr["custo_rastreamento"] = safe(rast_v[rast_v["Vencimento"].dt.month == m]["Valor"].sum()) if not rast_v.empty and "Vencimento" in rast_v.columns else 0.0
        mr["custo_total"]        = mr["custo_manutencao"] + mr["custo_seguro"] + mr["custo_rastreamento"]
        mr["margem"]             = mr["receita_total"] - mr["custo_total"]
        mr["dias_trabalhado"]    = safe(fat_v[fat_v["Mes"].dt.month == m]["Trabalhado"].sum()) if not fat_v.empty and "Mes" in fat_v.columns else 0.0
        monthly.append(mr)

    # Contract/region breakdown
    by_contract = []
    if not fat_v.empty and "Contrato" in fat_v.columns:
        grp = (fat_v.dropna(subset=["Contrato"])
               .groupby("Contrato", dropna=False)
               .agg(receita=("Medicao", "sum"),
                    dias_trab=("Trabalhado", "sum"),
                    dias_parado=("Parado", "sum"))
               .reset_index())
        for _, crow in grp.sort_values("receita", ascending=False).iterrows():
            by_contract.append({
                "contrato":       str(crow["Contrato"]),
                "receita":        safe(crow["receita"]),
                "dias_trabalhado": safe(crow["dias_trab"]),
                "dias_parado":    safe(crow["dias_parado"]),
                "diaria_media":   round(safe(crow["receita"]) / max(safe(crow["dias_trab"]), 1), 2),
            })

    # Maintenance detail
    maintenance = []
    if not manut_v.empty:
        for _, mrow in manut_v.iterrows():
            dt = mrow.get("DataExecução")
            maintenance.append({
                "ordem":           str(mrow.get("IDOrdServ", "—")),
                "data":            str(dt)[:10] if pd.notna(dt) else "—",
                "valor":           safe(mrow.get("TotalOS", 0)),
                "fornecedor":      str(mrow.get("Fornecedor", "—")),
                "sistema":         str(mrow.get("Sistema", "—")),
                "servico":         str(mrow.get("Serviço", "—")),
                "tipo":            str(mrow.get("TipoManutencao", "—")),
                "km":              safe(mrow.get("KM", 0)) if pd.notna(mrow.get("KM")) else None,
                "prox_km":         safe(mrow.get("ProxKM", 0)) if pd.notna(mrow.get("ProxKM")) else None,
                "prox_data":       str(mrow.get("ProxData", ""))[:10] if pd.notna(mrow.get("ProxData")) else None,
            })

    return {
        "info":        info,
        "kpis":        kpis_v,
        "monthly":     monthly,
        "by_contract": by_contract,
        "maintenance": sorted(maintenance, key=lambda x: x["data"], reverse=True),
    }


@app.get("/api/maintenance_analysis")
def get_maintenance_analysis(year: int = Query(...), placa: str = Query(None)):
    data = load_raw()
    manut_all = _parse(data["manutencoes"].copy(), "DataExecução")
    manut_yr  = _filter_year(manut_all, "DataExecução", year)
    manut     = _dedup_manut(manut_yr)

    if placa and "Placa" in manut.columns:
        manut = manut[manut["Placa"] == placa]

    result: dict = {}

    def _groupby_cost(df, col):
        if df.empty or col not in df.columns:
            return []
        g = (df.dropna(subset=[col])
             .groupby(col)
             .agg(total=("TotalOS", "sum"), count=("IDOrdServ", "nunique"))
             .reset_index()
             .sort_values("total", ascending=False))
        return [{"name": str(r[col]), "total": safe(r["total"]), "count": int(r["count"])} for _, r in g.iterrows()]

    result["by_fornecedor"] = _groupby_cost(manut, "Fornecedor")
    result["by_sistema"]    = _groupby_cost(manut, "Sistema")
    result["by_implemento"] = _groupby_cost(manut, "Implemento")
    result["by_servico"]    = _groupby_cost(manut, "Serviço")

    # Tipo (Preventiva/Corretiva)
    if not manut.empty and "TipoManutencao" in manut.columns:
        bt = (manut.dropna(subset=["TipoManutencao"])
              .groupby("TipoManutencao")["TotalOS"].sum().reset_index())
        result["by_tipo"] = [{"name": str(r["TipoManutencao"]), "total": safe(r["TotalOS"])} for _, r in bt.iterrows()]
    else:
        result["by_tipo"] = []

    # Categoria (Serviço/Compra)
    if not manut.empty and "Categoria" in manut.columns:
        bc = (manut.dropna(subset=["Categoria"])
              .groupby("Categoria")["TotalOS"].sum().reset_index())
        result["by_categoria"] = [{"name": str(r["Categoria"]), "total": safe(r["TotalOS"])} for _, r in bc.iterrows()]
    else:
        result["by_categoria"] = []

    # Monthly trend
    monthly_vals = []
    for m in range(1, 13):
        mv = 0.0
        if not manut.empty and "DataExecução" in manut.columns:
            mv = safe(manut[manut["DataExecução"].dt.month == m]["TotalOS"].sum())
        monthly_vals.append({"month": m, "name": MESES_PT[m - 1], "total": mv})
    result["monthly"] = monthly_vals

    # Linear projection (next 4 months)
    proj_input = [m["total"] for m in monthly_vals]
    result["projection"] = _linear_projection(proj_input, n_future=4)

    # KPI totals
    total_os_count = int(manut["IDOrdServ"].nunique()) if not manut.empty and "IDOrdServ" in manut.columns else 0
    total_cost     = safe(manut["TotalOS"].sum()) if not manut.empty else 0.0
    avg_per_os     = round(total_cost / total_os_count, 2) if total_os_count > 0 else 0.0
    top_forn       = result["by_fornecedor"][0]["name"] if result["by_fornecedor"] else "—"
    result["summary"] = {
        "total_os": total_os_count,
        "total_cost": total_cost,
        "avg_per_os": avg_per_os,
        "top_fornecedor": top_forn,
    }

    # Upcoming scheduled maintenance (ProxData or ProxKM)
    upcoming = []
    src = manut_all.copy()
    if placa and "Placa" in src.columns:
        src = src[src["Placa"] == placa]
    has_prox = src[(src["ProxData"].notna()) | (src["ProxKM"].notna())] if "ProxData" in src.columns else pd.DataFrame()
    if not has_prox.empty:
        seen = set()
        for _, mrow in has_prox.iterrows():
            key = (str(mrow.get("Placa", "")), str(mrow.get("Serviço", "")))
            if key in seen:
                continue
            seen.add(key)
            upcoming.append({
                "placa":      str(mrow.get("Placa", "—")),
                "modelo":     str(mrow.get("Modelo", "—")),
                "servico":    str(mrow.get("Serviço", "—")),
                "sistema":    str(mrow.get("Sistema", "—")),
                "km_atual":   safe(mrow["KM"]) if pd.notna(mrow.get("KM")) else None,
                "prox_km":    safe(mrow["ProxKM"]) if pd.notna(mrow.get("ProxKM")) else None,
                "prox_data":  str(mrow["ProxData"])[:10] if pd.notna(mrow.get("ProxData")) else None,
            })
            if len(upcoming) >= 30:
                break
    result["upcoming"] = upcoming

    return result
