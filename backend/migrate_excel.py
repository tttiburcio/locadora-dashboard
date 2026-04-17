"""
Importa os dados do Locadora.xlsx para o banco SQLite.

Uso:
    cd backend
    python migrate_excel.py

Seguro para rodar mais de uma vez: apaga e recria todas as tabelas.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Permite rodar diretamente (sem ser módulo do pacote)
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from database import engine, Base, SessionLocal
import models  # noqa — registra os modelos no Base.metadata

EXCEL = ROOT / "Locadora.xlsx"

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


def _v(val, default=None):
    """Converte NaN/NaT para None."""
    if val is None:
        return default
    try:
        if isinstance(val, float) and np.isnan(val):
            return default
    except TypeError:
        pass
    if pd.isna(val):
        return default
    return val


def _date(val):
    """Converte para date Python ou None."""
    v = _v(val)
    if v is None:
        return None
    try:
        return pd.Timestamp(v).date()
    except Exception:
        return None


def _float(val):
    v = _v(val)
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _int(val):
    v = _v(val)
    if v is None:
        return None
    try:
        return int(float(v))
    except Exception:
        return None


def _str(val):
    v = _v(val)
    if v is None:
        return None
    s = str(v).strip()
    return s if s and s.lower() != "nan" else None


# ─────────────────────────────────────────────────────────────────────
def load_sheets() -> dict:
    print(f"Lendo {EXCEL.name}…")
    raw = {}
    with pd.ExcelFile(EXCEL) as xl:
        for key, name in SHEETS.items():
            try:
                raw[key] = xl.parse(name)
                print(f"  OK [{key}]  ({len(raw[key])} linhas)")
            except Exception as e:
                print(f"  ERRO [{key}]: {e}")
                raw[key] = pd.DataFrame()
    return raw


# ─────────────────────────────────────────────────────────────────────
def migrate_frota(session, df: pd.DataFrame):
    print("\n[FROTA]")
    count = 0
    for _, row in df.iterrows():
        id_v = _int(row.get("IDVeiculo"))
        placa = _str(row.get("Placa"))
        if not id_v or not placa:
            continue
        obj = models.Frota(
            id=id_v,
            placa=placa,
            empresa=_str(row.get("Empresa")),
            marca=_str(row.get("Marca")),
            modelo=_str(row.get("Modelo")),
            status=_str(row.get("Status")),
            tipagem=_str(row.get("Tipagem")),
            implemento=_str(row.get("Implemento")),
            valor_total=_float(row.get("ValorTotal")),
        )
        session.merge(obj)
        count += 1
    session.flush()
    print(f"  {count} veículos importados")


# ─────────────────────────────────────────────────────────────────────
def migrate_manutencoes(session, df: pd.DataFrame):
    """
    Regra de normalização:
    - Linhas com IDOrdServ: agrupa por IDOrdServ → 1 Manutencao + N parcelas
    - Linhas sem IDOrdServ: cada linha → 1 Manutencao sem parcelas
    Todos os registros vindos do Excel são marcados como 'finalizada'.
    """
    print("\n[MANUTENCOES]")
    if df.empty:
        print("  sem dados")
        return

    # Normaliza coluna de data (nome com encoding variável)
    date_col = next((c for c in df.columns if "DataExecu" in c or "Data Execu" in c), None)
    if date_col:
        df["_data"] = pd.to_datetime(df[date_col], errors="coerce")
    else:
        df["_data"] = pd.NaT

    # Coluna de serviço pode ter encoding diferente
    serv_col = next((c for c in df.columns if "Servi" in c), "Serviço")

    # Separa com e sem OS
    has_os = df[df["IDOrdServ"].notna()].copy()
    no_os  = df[df["IDOrdServ"].isna()].copy()

    count_manut = 0
    count_parc  = 0

    # ── Com OS: 1 OS → N parcelas ───────────────────────────────────
    for id_ord_serv, grp in has_os.groupby("IDOrdServ"):
        first = grp.iloc[0]
        manut = models.Manutencao(
            status_manutencao="finalizada",
            id_veiculo=_int(first.get("IDVeiculo")),
            placa=_str(first.get("Placa")),
            modelo=_str(first.get("Modelo")),
            empresa=_str(first.get("Empresa")) or _str(first.get("IDContrato")),
            id_contrato=_str(first.get("IDContrato")),
            implemento=_str(first.get("Implemento")),
            fornecedor=_str(first.get("Fornecedor")),
            tipo_manutencao=_str(first.get("TipoManutencao")),
            sistema=_str(first.get("Sistema")),
            servico=_str(first.get(serv_col)),
            descricao=_str(first.get("Descricao")),
            qtd_itens=_int(first.get("QtdItens")),
            km=_float(first.get("KM")),
            posicao_pneu=_str(first.get("PosicaoPneu")) or _str(first.get("Posição Pneu")) or _str(first.get("Posição do Pneu")),
            qtd_pneu=_int(first.get("QtdPneu")),
            espec_pneu=_str(first.get("EspecificacaoPneu")) or _str(first.get("Especificação Pneu")),
            marca_pneu=_str(first.get("MarcaPneu")),
            manejo_pneu=_str(first.get("ManejoPneu")),
            responsavel_tec=_str(first.get("ResponsavelTec")),
            indisponivel=bool(_v(first.get("Indisponível"), False)),
            data_execucao=_date(first.get("_data")),
            id_ord_serv=_str(id_ord_serv),
            total_os=_float(first.get("TotalOS")),
            valida_nova_os=_str(first.get("ValidaNovaOS")),
            categoria=_str(first.get("Categoria")),
            prox_km=_float(first.get("ProxKM")),
            prox_data=_date(first.get("ProxData")),
            observacoes=_str(first.get("Obsercacoes")),
        )
        # Garante id_veiculo preenchido
        if not manut.id_veiculo:
            continue

        session.add(manut)
        session.flush()
        count_manut += 1

        for _, prow in grp.iterrows():
            # Data Venc. pode ter espaço no nome
            venc_col = next((c for c in prow.index if "Venc" in c and "Data" in c), "Data Venc.")
            parcela = models.ManutencaoParcela(
                manutencao_id=manut.id,
                nf_ordem=_int(prow.get("NFOrdem")),
                nota=_str(prow.get("Nota")),
                data_vencimento=_date(prow.get(venc_col)),
                parcela_atual=_int(prow.get("ParcelaAtual")),
                parcela_total=_int(prow.get("ParcelaTotal")),
                valor_parcela=_float(prow.get("ValorParcela")),
                forma_pgto=_str(prow.get("FormaPgto")),
                status_pagamento=_str(prow.get("Status")) or "Pago",
            )
            session.add(parcela)
            count_parc += 1

    # ── Sem OS: cada linha vira 1 manutenção independente ───────────
    for _, row in no_os.iterrows():
        if not _int(row.get("IDVeiculo")):
            continue
        manut = models.Manutencao(
            status_manutencao="finalizada",
            id_veiculo=_int(row.get("IDVeiculo")),
            placa=_str(row.get("Placa")),
            modelo=_str(row.get("Modelo")),
            empresa=_str(row.get("Empresa")),
            id_contrato=_str(row.get("IDContrato")),
            implemento=_str(row.get("Implemento")),
            fornecedor=_str(row.get("Fornecedor")),
            tipo_manutencao=_str(row.get("TipoManutencao")),
            sistema=_str(row.get("Sistema")),
            servico=_str(row.get(serv_col)),
            descricao=_str(row.get("Descricao")),
            km=_float(row.get("KM")),
            responsavel_tec=_str(row.get("ResponsavelTec")),
            indisponivel=bool(_v(row.get("Indisponível"), False)),
            data_execucao=_date(row.get("_data")),
            total_os=_float(row.get("TotalOS")),
            categoria=_str(row.get("Categoria")),
            prox_km=_float(row.get("ProxKM")),
            prox_data=_date(row.get("ProxData")),
            observacoes=_str(row.get("Obsercacoes")),
        )
        session.add(manut)
        count_manut += 1

    session.flush()
    print(f"  {count_manut} OS importadas  |  {count_parc} parcelas")


# ─────────────────────────────────────────────────────────────────────
def migrate_fat_unitario(session, df: pd.DataFrame):
    print("\n[FAT_UNITARIO]")
    count = 0
    for _, row in df.iterrows():
        id_v = _int(row.get("IDVeiculo"))
        if not id_v:
            continue
        obj = models.FatUnitario(
            mes=_date(row.get("Mes")),
            id_veiculo=id_v,
            contrato=_str(row.get("Contrato")),
            medicao=_float(row.get("Medicao")),
            trabalhado=_int(row.get("Trabalhado")),
            parado=_int(row.get("Parado")),
        )
        session.add(obj)
        count += 1
    session.flush()
    print(f"  {count} registros")


def migrate_reembolsos(session, df: pd.DataFrame):
    print("\n[REEMBOLSOS]")
    count = 0
    for _, row in df.iterrows():
        id_v = _int(row.get("IDVeiculo"))
        if not id_v:
            continue
        obj = models.Reembolso(
            emissao=_date(row.get("Emissão")),
            id_veiculo=id_v,
            valor_reembolso=_float(row.get("ValorReembolso")),
        )
        session.add(obj)
        count += 1
    session.flush()
    print(f"  {count} registros")


def migrate_faturamento(session, df: pd.DataFrame):
    print("\n[FATURAMENTO]")
    count = 0
    for _, row in df.iterrows():
        obj = models.Faturamento(
            emissao=_date(row.get("Emissão")),
            valor_locacoes=_float(row.get("ValorLocacoes")),
            valor_recebido=_float(row.get("ValorRecebido")),
        )
        session.add(obj)
        count += 1
    session.flush()
    print(f"  {count} registros")


def migrate_seguro(session, df: pd.DataFrame):
    print("\n[SEGURO_MENSAL]")
    count = 0
    for _, row in df.iterrows():
        id_v = _int(row.get("IDVeiculo"))
        if not id_v:
            continue
        obj = models.SeguroMensal(
            vencimento=_date(row.get("Vencimento")),
            id_veiculo=id_v,
            valor=_float(row.get("Valor")),
        )
        session.add(obj)
        count += 1
    session.flush()
    print(f"  {count} registros")


def migrate_impostos(session, df: pd.DataFrame):
    print("\n[IMPOSTOS]")
    count = 0
    for _, row in df.iterrows():
        id_v = _int(row.get("IDVeiculo"))
        if not id_v:
            continue
        val_col = "ValorTotalFinal" if "ValorTotalFinal" in row.index else None
        if not val_col:
            val = (_float(row.get("ValorIpva")) or 0) + (_float(row.get("ValorLicenc")) or 0)
        else:
            val = _float(row.get(val_col))
        obj = models.Imposto(
            ano_imposto=_int(row.get("AnoImposto")),
            id_veiculo=id_v,
            valor_total_final=val,
        )
        session.add(obj)
        count += 1
    session.flush()
    print(f"  {count} registros")


def migrate_rastreamento(session, df: pd.DataFrame):
    print("\n[RASTREAMENTO]")
    count = 0
    for _, row in df.iterrows():
        id_v = _int(row.get("IDVeiculo"))
        if not id_v:
            continue
        obj = models.Rastreamento(
            vencimento=_date(row.get("Vencimento")),
            id_veiculo=id_v,
            valor=_float(row.get("Valor")),
        )
        session.add(obj)
        count += 1
    session.flush()
    print(f"  {count} registros")


# ─────────────────────────────────────────────────────────────────────
def run():
    print("=" * 55)
    print("  MIGRACAO Excel -> SQLite")
    print(f"  Destino: {ROOT / 'locadora.db'}")
    print("=" * 55)

    # Recria o schema limpo
    print("\nRecriando tabelas…")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    raw = load_sheets()

    with SessionLocal() as session:
        migrate_frota(session, raw["frota"])
        migrate_manutencoes(session, raw["manutencoes"])
        migrate_fat_unitario(session, raw["fat_unitario"])
        migrate_reembolsos(session, raw["reembolsos"])
        migrate_faturamento(session, raw["faturamento"])
        migrate_seguro(session, raw["seguro_mensal"])
        migrate_impostos(session, raw["impostos"])
        migrate_rastreamento(session, raw["rastreamento"])
        session.commit()

    print("\nMigracao concluida com sucesso.")


if __name__ == "__main__":
    run()
