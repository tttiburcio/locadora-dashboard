import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# ─────────────────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Locadora",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

EXCEL_PATH = "Locadora.xlsx"

SHEETS = {
    "frota":         "🚛 FROTA",
    "fat_unitario":  "💰 FAT_UNITARIO",
    "reembolsos":    "↩️ REEMBOLSOS",
    "manutencoes":   "🔧 MANUTENCOES",
    "faturamento":   "🧾 FATURAMENTO",
    "seguro_mensal": "📋 SEGURO_MENSAL",
    "impostos":      "📋 IMPOSTOS",
    "rastreamento":  "📍RASTREAMENTO",
}

CORES = {
    "locacao":      "#3B82F6",   # azul
    "reembolso":    "#10B981",   # verde-água
    "manutencao":   "#F97316",   # laranja
    "seguro":       "#EF4444",   # vermelho
    "impostos":     "#8B5CF6",   # roxo
    "rastreamento": "#F59E0B",   # âmbar
    "positivo":     "#22C55E",   # verde
    "negativo":     "#EF4444",   # vermelho
    "grid":         "rgba(100,100,120,0.2)",
}

MESES_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
    5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────
def fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def layout_base(title: str, height: int = 420) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=15)),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="#1e1e2e", font_color="#cdd6f4"),
    )


def axis_brl(fig, axis: str = "x") -> None:
    update = dict(
        tickformat=",.0f",
        tickprefix="R$ ",
        gridcolor=CORES["grid"],
        zeroline=False,
    )
    if axis == "x":
        fig.update_xaxes(**update)
    else:
        fig.update_yaxes(**update)


# ─────────────────────────────────────────────────────────
# CARREGAMENTO DE DADOS
# ─────────────────────────────────────────────────────────
@st.cache_data
def load_raw() -> dict:
    xl = pd.ExcelFile(EXCEL_PATH)
    return {key: xl.parse(name) for key, name in SHEETS.items()}


@st.cache_data
def get_years() -> list[int]:
    data = load_raw()
    years: set = set()
    fat = data["fat_unitario"]
    if "Mes" in fat.columns:
        years.update(fat["Mes"].dropna().dt.year.unique())
    fatu = data["faturamento"]
    if "Emissão" in fatu.columns:
        years.update(fatu["Emissão"].dropna().dt.year.unique())
    return sorted([int(y) for y in years], reverse=True)


@st.cache_data
def process(year: int):
    data = load_raw()

    frota   = data["frota"].copy()
    fat     = data["fat_unitario"].copy()
    reimb   = data["reembolsos"].copy()
    manut   = data["manutencoes"].copy()
    fat_sh  = data["faturamento"].copy()
    seg     = data["seguro_mensal"].copy()
    imp     = data["impostos"].copy()
    rast    = data["rastreamento"].copy()

    # ── Filtrar por ano ───────────────────────────────────
    fat_y    = fat[fat["Mes"].dt.year == year].copy()
    reimb_y  = reimb[reimb["Emissão"].dt.year == year].copy()
    # MANUTENCOES: usa DataExecução como referência do custo; deduplica por IDOrdServ
    # porque TotalOS é o valor total da OS, repetido em cada linha de parcela/categoria
    manut_y  = manut[manut["DataExecução"].dt.year == year].copy()
    manut_com_os  = manut_y.dropna(subset=["IDOrdServ"]).drop_duplicates(subset=["IDOrdServ"])
    manut_sem_os  = manut_y[manut_y["IDOrdServ"].isna()]
    manut_dedup   = pd.concat([manut_com_os, manut_sem_os], ignore_index=True)
    fat_sh_y = fat_sh[fat_sh["Emissão"].dt.year == year].copy()
    seg_y    = seg[seg["Vencimento"].dt.year == year].copy()
    imp_y    = imp[imp["AnoImposto"] == year].copy()
    rast_y   = rast[rast["Vencimento"].dt.year == year].copy()

    # ── Receita por veículo ───────────────────────────────
    rev_loc   = (fat_y.groupby("IDVeiculo")["Medicao"].sum()
                 .rename("ReceitaLocacao"))
    rev_reimb = (reimb_y.dropna(subset=["IDVeiculo"])
                 .groupby("IDVeiculo")["ValorReembolso"].sum()
                 .rename("ReceitaReembolso"))

    # ── Custo por veículo ─────────────────────────────────
    cost_manut = (manut_dedup.dropna(subset=["IDVeiculo"])
                  .groupby("IDVeiculo")["TotalOS"].sum()
                  .rename("CustoManutencao"))
    cost_seg   = (seg_y.groupby("IDVeiculo")["Valor"].sum()
                  .rename("CustoSeguro"))
    cost_imp   = (imp_y.groupby("IDVeiculo")["ValorTotalFinal"].sum()
                  .rename("CustoImpostos"))
    cost_rast  = (rast_y.groupby("IDVeiculo")["Valor"].sum()
                  .rename("CustoRastreamento"))

    # ── Dias por veículo ──────────────────────────────────
    dias = fat_y.groupby("IDVeiculo").agg(
        Trabalhado=("Trabalhado", "sum"),
        Parado=("Parado", "sum"),
    )

    # ── Tabela consolidada por veículo ────────────────────
    df = (
        frota[["IDVeiculo", "Placa", "Marca", "Modelo", "Status"]]
        .set_index("IDVeiculo")
        .join(rev_loc, how="left")
        .join(rev_reimb, how="left")
        .join(cost_manut, how="left")
        .join(cost_seg, how="left")
        .join(cost_imp, how="left")
        .join(cost_rast, how="left")
        .join(dias, how="left")
        .fillna(0)
        .reset_index()
    )

    df["ReceitaTotal"] = df["ReceitaLocacao"] + df["ReceitaReembolso"]
    df["CustoTotal"]   = (df["CustoManutencao"] + df["CustoSeguro"]
                          + df["CustoImpostos"] + df["CustoRastreamento"])
    df["Margem"]       = df["ReceitaTotal"] - df["CustoTotal"]
    df["MargemPct"]    = np.where(
        df["ReceitaTotal"] > 0,
        df["Margem"] / df["ReceitaTotal"] * 100,
        0,
    )
    df["Veiculo"] = df["Placa"] + "  " + df["Modelo"]

    df_active = df[(df["ReceitaTotal"] > 0) | (df["CustoTotal"] > 0)].copy()

    # ── Evolução mensal ───────────────────────────────────
    def monthly_group(frame, date_col, value_col, out_col):
        if frame.empty:
            return pd.DataFrame(columns=["Mes", out_col])
        return (
            frame.assign(_p=frame[date_col].dt.to_period("M"))
            .groupby("_p")[value_col].sum()
            .reset_index()
            .assign(Mes=lambda d: d["_p"].dt.to_timestamp())
            .drop(columns="_p")
            .rename(columns={value_col: out_col})
        )

    monthly_loc   = monthly_group(fat_y,   "Mes",     "Medicao",        "Locacao")
    monthly_reimb = monthly_group(reimb_y, "Emissão", "ValorReembolso", "Reembolso")
    monthly_cost_manut = monthly_group(
        manut_dedup.dropna(subset=["IDVeiculo"]), "DataExecução", "TotalOS", "CustoManutencao"
    )
    monthly_cost_seg  = monthly_group(seg_y,  "Vencimento", "Valor",          "CustoSeguro")
    monthly_cost_rast = monthly_group(rast_y, "Vencimento", "Valor",          "CustoRastreamento")

    monthly = (
        monthly_loc
        .merge(monthly_reimb,      on="Mes", how="outer")
        .merge(monthly_cost_manut, on="Mes", how="outer")
        .merge(monthly_cost_seg,   on="Mes", how="outer")
        .merge(monthly_cost_rast,  on="Mes", how="outer")
        .fillna(0)
        .sort_values("Mes")
        .reset_index(drop=True)
    )
    monthly["ReceitaTotal"] = monthly["Locacao"] + monthly["Reembolso"]
    monthly["CustoTotal"]   = (monthly["CustoManutencao"]
                                + monthly["CustoSeguro"]
                                + monthly["CustoRastreamento"])
    monthly["MesLabel"] = monthly["Mes"].dt.month.map(MESES_PT)

    # ── KPIs gerais ───────────────────────────────────────
    kpis = {
        "faturado":     fat_sh_y["ValorLocacoes"].sum(),
        "recebido":     fat_sh_y["ValorRecebido"].sum(),
        "reembolsos":   reimb_y["ValorReembolso"].sum(),
        "custo":        df_active["CustoTotal"].sum(),
        "veiculos_ativos": len(df_active),
    }
    kpis["receita_total"] = kpis["faturado"] + kpis["reembolsos"]
    kpis["margem"]        = kpis["receita_total"] - kpis["custo"]
    kpis["margem_pct"]    = (
        kpis["margem"] / kpis["receita_total"] * 100
        if kpis["receita_total"] > 0 else 0
    )

    return df_active, monthly, kpis


# ─────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🚛 Locadora")
    st.divider()

    years = get_years()
    if not years:
        st.error("Nenhum dado encontrado na planilha.")
        st.stop()

    year = st.selectbox("📅  Ano de análise", years, index=0)

    st.divider()
    st.caption("**Receita**")
    st.markdown("&nbsp;&nbsp;• Locação · FAT_UNITARIO")
    st.markdown("&nbsp;&nbsp;• Reembolsos · multas / manutenção / seguro")
    st.caption("**Custo**")
    st.markdown("&nbsp;&nbsp;• Manutenção")
    st.markdown("&nbsp;&nbsp;• Seguro mensal")
    st.markdown("&nbsp;&nbsp;• Impostos (IPVA / Licenc. / Multas)")
    st.markdown("&nbsp;&nbsp;• Rastreamento")

# ─────────────────────────────────────────────────────────
# CARREGAR DADOS
# ─────────────────────────────────────────────────────────
with st.spinner("Carregando dados..."):
    df, monthly, kpis = process(year)

if df.empty:
    st.warning(f"Nenhum dado encontrado para o ano {year}.")
    st.stop()

# ─────────────────────────────────────────────────────────
# CABEÇALHO
# ─────────────────────────────────────────────────────────
st.markdown(f"# Dashboard Financeiro — {year}")
st.caption("Análise anual de faturamento e custos por veículo · dados consolidados da planilha Locadora.xlsx")

# ─────────────────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("🗂️  Veículos ativos",  kpis["veiculos_ativos"])
c2.metric("📄  Faturado",          fmt_brl(kpis["faturado"]))
c3.metric("✅  Recebido",           fmt_brl(kpis["recebido"]))
c4.metric("↩️  Reembolsos",         fmt_brl(kpis["reembolsos"]))
c5.metric("🔧  Custo Total",        fmt_brl(kpis["custo"]))
c6.metric(
    "💰  Margem",
    fmt_brl(kpis["margem"]),
    delta=f"{kpis['margem_pct']:.1f}%",
    delta_color="normal",
)

st.divider()

# ═════════════════════════════════════════════════════════
# SEÇÃO 1 · FATURAMENTO
# ═════════════════════════════════════════════════════════
st.subheader("Faturamento")

# ── 1a. Evolução mensal de receita ────────────────────────
if not monthly.empty:
    fig_mensal = go.Figure()
    fig_mensal.add_trace(go.Bar(
        x=monthly["MesLabel"],
        y=monthly["Locacao"],
        name="Locação",
        marker_color=CORES["locacao"],
        hovertemplate="<b>%{x}</b><br>Locação: R$ %{y:,.2f}<extra></extra>",
    ))
    fig_mensal.add_trace(go.Bar(
        x=monthly["MesLabel"],
        y=monthly["Reembolso"],
        name="Reembolso",
        marker_color=CORES["reembolso"],
        hovertemplate="<b>%{x}</b><br>Reembolso: R$ %{y:,.2f}<extra></extra>",
    ))
    fig_mensal.add_trace(go.Scatter(
        x=monthly["MesLabel"],
        y=monthly["ReceitaTotal"],
        name="Receita Total",
        mode="lines+markers",
        line=dict(color="white", width=2, dash="dot"),
        marker=dict(size=6),
        hovertemplate="<b>%{x}</b><br>Total: R$ %{y:,.2f}<extra></extra>",
    ))
    fig_mensal.update_layout(
        **layout_base("Evolução Mensal da Receita", height=380),
        barmode="stack",
        xaxis=dict(gridcolor=CORES["grid"]),
        yaxis=dict(tickformat=",.0f", tickprefix="R$ ", gridcolor=CORES["grid"]),
    )
    st.plotly_chart(fig_mensal, use_container_width=True)

# ── 1b. Receita por veículo ───────────────────────────────
df_rev = df.sort_values("ReceitaTotal", ascending=True)
height_rev = max(380, len(df_rev) * 32 + 80)

fig_rev = go.Figure()
fig_rev.add_trace(go.Bar(
    y=df_rev["Veiculo"],
    x=df_rev["ReceitaLocacao"],
    name="Locação",
    orientation="h",
    marker_color=CORES["locacao"],
    hovertemplate="<b>%{y}</b><br>Locação: R$ %{x:,.2f}<extra></extra>",
))
fig_rev.add_trace(go.Bar(
    y=df_rev["Veiculo"],
    x=df_rev["ReceitaReembolso"],
    name="Reembolso",
    orientation="h",
    marker_color=CORES["reembolso"],
    hovertemplate="<b>%{y}</b><br>Reembolso: R$ %{x:,.2f}<extra></extra>",
))
fig_rev.update_layout(
    **layout_base("Receita Total por Veículo", height=height_rev),
    barmode="stack",
    xaxis=dict(tickformat=",.0f", tickprefix="R$ ", gridcolor=CORES["grid"]),
    yaxis=dict(gridcolor=CORES["grid"]),
    margin=dict(l=200, r=10, t=50, b=10),
)
st.plotly_chart(fig_rev, use_container_width=True)

st.divider()

# ═════════════════════════════════════════════════════════
# SEÇÃO 2 · CUSTOS E COMPARATIVO
# ═════════════════════════════════════════════════════════
st.subheader("Custos e Comparativo")

# ── 2a. Composição de custos por veículo ─────────────────
df_cost = df.sort_values("CustoTotal", ascending=True)
height_cost = max(380, len(df_cost) * 32 + 80)

fig_cost = go.Figure()
custo_cols = [
    ("CustoManutencao",   "Manutenção",   CORES["manutencao"]),
    ("CustoSeguro",       "Seguro",        CORES["seguro"]),
    ("CustoImpostos",     "Impostos",      CORES["impostos"]),
    ("CustoRastreamento", "Rastreamento",  CORES["rastreamento"]),
]
for col, label, cor in custo_cols:
    fig_cost.add_trace(go.Bar(
        y=df_cost["Veiculo"],
        x=df_cost[col],
        name=label,
        orientation="h",
        marker_color=cor,
        hovertemplate=f"<b>%{{y}}</b><br>{label}: R$ %{{x:,.2f}}<extra></extra>",
    ))
fig_cost.update_layout(
    **layout_base("Composição de Custos por Veículo", height=height_cost),
    barmode="stack",
    xaxis=dict(tickformat=",.0f", tickprefix="R$ ", gridcolor=CORES["grid"]),
    yaxis=dict(gridcolor=CORES["grid"]),
    margin=dict(l=200, r=10, t=50, b=10),
)
st.plotly_chart(fig_cost, use_container_width=True)

# ── 2b. Faturamento vs Custo por veículo ─────────────────
df_cmp = df.sort_values("ReceitaTotal", ascending=False)
height_cmp = max(420, len(df_cmp) * 22 + 100)

fig_cmp = go.Figure()
fig_cmp.add_trace(go.Bar(
    x=df_cmp["Veiculo"],
    y=df_cmp["ReceitaTotal"],
    name="Receita Total",
    marker_color=CORES["locacao"],
    hovertemplate="<b>%{x}</b><br>Receita: R$ %{y:,.2f}<extra></extra>",
))
fig_cmp.add_trace(go.Bar(
    x=df_cmp["Veiculo"],
    y=df_cmp["CustoTotal"],
    name="Custo Total",
    marker_color=CORES["manutencao"],
    hovertemplate="<b>%{x}</b><br>Custo: R$ %{y:,.2f}<extra></extra>",
))
fig_cmp.update_layout(
    **layout_base("Faturamento vs Custo por Veículo", height=height_cmp),
    barmode="group",
    xaxis=dict(tickangle=-35, gridcolor=CORES["grid"]),
    yaxis=dict(tickformat=",.0f", tickprefix="R$ ", gridcolor=CORES["grid"]),
)
st.plotly_chart(fig_cmp, use_container_width=True)

# ── 2c. Margem + Scatter ──────────────────────────────────
col_esq, col_dir = st.columns(2)

with col_esq:
    df_mg = df.sort_values("Margem", ascending=True)
    cores_mg = [CORES["positivo"] if v >= 0 else CORES["negativo"] for v in df_mg["Margem"]]
    height_mg = max(380, len(df_mg) * 28 + 80)

    fig_mg = go.Figure()
    fig_mg.add_vline(x=0, line_color="rgba(200,200,220,0.4)", line_width=1)
    fig_mg.add_trace(go.Bar(
        y=df_mg["Veiculo"],
        x=df_mg["Margem"],
        orientation="h",
        marker_color=cores_mg,
        hovertemplate="<b>%{y}</b><br>Margem: R$ %{x:,.2f}<extra></extra>",
        showlegend=False,
    ))
    fig_mg.update_layout(
        **layout_base("Margem por Veículo  (Receita − Custo)", height=height_mg),
        xaxis=dict(tickformat=",.0f", tickprefix="R$ ", gridcolor=CORES["grid"]),
        yaxis=dict(gridcolor=CORES["grid"]),
        margin=dict(l=200, r=10, t=50, b=10),
    )
    st.plotly_chart(fig_mg, use_container_width=True)

with col_dir:
    df_sc = df.copy()
    max_trab = df_sc["Trabalhado"].max()
    bubble_size = np.where(
        df_sc["Trabalhado"] > 0,
        df_sc["Trabalhado"] / max(max_trab, 1) * 40 + 8,
        10,
    )
    cores_sc = [CORES["positivo"] if m >= 0 else CORES["negativo"] for m in df_sc["Margem"]]

    max_val = max(df_sc[["ReceitaTotal", "CustoTotal"]].values.max(), 1)

    fig_sc = go.Figure()
    # Linha break-even (custo = receita)
    fig_sc.add_trace(go.Scatter(
        x=[0, max_val * 1.05],
        y=[0, max_val * 1.05],
        mode="lines",
        name="Break-even",
        line=dict(color="rgba(200,200,220,0.35)", dash="dash", width=1.5),
        hoverinfo="skip",
    ))
    # Anotação nas zonas
    fig_sc.add_annotation(
        x=max_val * 0.75, y=max_val * 0.55,
        text="✅ Receita > Custo", showarrow=False,
        font=dict(color=CORES["positivo"], size=11),
    )
    fig_sc.add_annotation(
        x=max_val * 0.35, y=max_val * 0.75,
        text="❌ Custo > Receita", showarrow=False,
        font=dict(color=CORES["negativo"], size=11),
    )
    fig_sc.add_trace(go.Scatter(
        x=df_sc["ReceitaTotal"],
        y=df_sc["CustoTotal"],
        mode="markers+text",
        text=df_sc["Placa"],
        textposition="top center",
        textfont=dict(size=9),
        marker=dict(
            size=bubble_size,
            color=cores_sc,
            line=dict(width=1, color="rgba(255,255,255,0.3)"),
            opacity=0.85,
        ),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Receita: R$ %{x:,.2f}<br>"
            "Custo: R$ %{y:,.2f}<br>"
            "Dias trabalhados: %{customdata[1]:.0f}<br>"
            "Margem: R$ %{customdata[2]:,.2f}<extra></extra>"
        ),
        customdata=df_sc[["Veiculo", "Trabalhado", "Margem"]].values,
        showlegend=False,
    ))
    fig_sc.update_layout(
        **layout_base("Receita × Custo  (bolha = dias trabalhados)", height=height_mg),
        xaxis=dict(title="Receita (R$)", tickformat=",.0f", gridcolor=CORES["grid"]),
        yaxis=dict(title="Custo (R$)", tickformat=",.0f", gridcolor=CORES["grid"]),
    )
    st.plotly_chart(fig_sc, use_container_width=True)

# ── 2d. Evolução mensal de receita vs custo ───────────────
if not monthly.empty:
    fig_mc = go.Figure()
    fig_mc.add_trace(go.Bar(
        x=monthly["MesLabel"],
        y=monthly["CustoManutencao"],
        name="Manutenção",
        marker_color=CORES["manutencao"],
        hovertemplate="<b>%{x}</b><br>Manutenção: R$ %{y:,.2f}<extra></extra>",
    ))
    fig_mc.add_trace(go.Bar(
        x=monthly["MesLabel"],
        y=monthly["CustoSeguro"],
        name="Seguro",
        marker_color=CORES["seguro"],
        hovertemplate="<b>%{x}</b><br>Seguro: R$ %{y:,.2f}<extra></extra>",
    ))
    fig_mc.add_trace(go.Bar(
        x=monthly["MesLabel"],
        y=monthly["CustoRastreamento"],
        name="Rastreamento",
        marker_color=CORES["rastreamento"],
        hovertemplate="<b>%{x}</b><br>Rastreamento: R$ %{y:,.2f}<extra></extra>",
    ))
    fig_mc.add_trace(go.Scatter(
        x=monthly["MesLabel"],
        y=monthly["ReceitaTotal"],
        name="Receita Total",
        mode="lines+markers",
        line=dict(color=CORES["locacao"], width=2.5),
        marker=dict(size=7),
        hovertemplate="<b>%{x}</b><br>Receita: R$ %{y:,.2f}<extra></extra>",
    ))
    fig_mc.update_layout(
        **layout_base("Receita vs Custos Mensais", height=400),
        barmode="stack",
        xaxis=dict(gridcolor=CORES["grid"]),
        yaxis=dict(tickformat=",.0f", tickprefix="R$ ", gridcolor=CORES["grid"]),
    )
    st.plotly_chart(fig_mc, use_container_width=True)

st.divider()

# ═════════════════════════════════════════════════════════
# SEÇÃO 3 · RANKING DE RENTABILIDADE
# ═════════════════════════════════════════════════════════
st.subheader("Ranking de Rentabilidade")

tabela = (
    df.sort_values("Margem", ascending=False)
    [[
        "Placa", "Modelo", "Status",
        "ReceitaLocacao", "ReceitaReembolso", "ReceitaTotal",
        "CustoManutencao", "CustoSeguro", "CustoImpostos", "CustoRastreamento", "CustoTotal",
        "Margem", "MargemPct", "Trabalhado",
    ]]
    .reset_index(drop=True)
)

tabela.index = tabela.index + 1  # posição no ranking

st.dataframe(
    tabela,
    use_container_width=True,
    column_config={
        "Placa":              st.column_config.TextColumn("Placa"),
        "Modelo":             st.column_config.TextColumn("Modelo"),
        "Status":             st.column_config.TextColumn("Status"),
        "ReceitaLocacao":     st.column_config.NumberColumn("Rec. Locação",   format="R$ %.2f"),
        "ReceitaReembolso":   st.column_config.NumberColumn("Rec. Reembolso", format="R$ %.2f"),
        "ReceitaTotal":       st.column_config.NumberColumn("Receita Total",  format="R$ %.2f"),
        "CustoManutencao":    st.column_config.NumberColumn("Manutenção",     format="R$ %.2f"),
        "CustoSeguro":        st.column_config.NumberColumn("Seguro",         format="R$ %.2f"),
        "CustoImpostos":      st.column_config.NumberColumn("Impostos",       format="R$ %.2f"),
        "CustoRastreamento":  st.column_config.NumberColumn("Rastreamento",   format="R$ %.2f"),
        "CustoTotal":         st.column_config.NumberColumn("Custo Total",    format="R$ %.2f"),
        "Margem":             st.column_config.NumberColumn("Margem",         format="R$ %.2f"),
        "MargemPct":          st.column_config.NumberColumn("% Margem",       format="%.1f%%"),
        "Trabalhado":         st.column_config.NumberColumn("Dias Trab.",     format="%d dias"),
    },
)

st.caption(
    "⚠️ Custos de manutenção contabilizados pela data de execução da OS · "
    "Impostos filtrados pelo campo AnoImposto · "
    "Seguro e rastreamento pelo vencimento da parcela"
)
