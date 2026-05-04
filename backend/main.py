from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, selectinload
import pandas as pd
import numpy as np
from pathlib import Path
import io
import logging

# ── Banco de dados ────────────────────────────────────────────────
from database import get_db, init_db, engine
import models
import schemas

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("locadora")

app = FastAPI(title="TKJ Locadora API", version="2.1.0")


@app.on_event("startup")
def startup():
    init_db()
    _migrate_parcelas_prorrogacao()
    _migrate_1to1_safe()


def _migrate_parcelas_prorrogacao():
    import sqlite3
    from database import DB_PATH

    # DDL completo da tabela com manutencao_id nullable
    NEW_TABLE_DDL = """
        CREATE TABLE manutencao_parcelas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manutencao_id INTEGER REFERENCES manutencoes(id),
            nf_ordem INTEGER,
            nota VARCHAR(50),
            fornecedor VARCHAR(120),
            valor_item_total NUMERIC(14,2),
            tipo_custo VARCHAR(30),
            data_vencimento DATE,
            parcela_atual INTEGER,
            parcela_total INTEGER,
            valor_parcela NUMERIC(14,2),
            forma_pgto VARCHAR(50),
            status_pagamento VARCHAR(20) DEFAULT 'Pendente',
            data_vencimento_original DATE,
            prorrogada BOOLEAN DEFAULT 0,
            isento_encargos BOOLEAN,
            tipo_pgto_prorrogacao VARCHAR(20),
            chave_pix VARCHAR(100),
            multa_pct NUMERIC(6,2),
            juros_diario_pct NUMERIC(6,4),
            data_prevista_pagamento DATE,
            dias_cartorio INTEGER,
            valor_atualizado NUMERIC(14,2),
            sera_reembolsado BOOLEAN DEFAULT 0,
            valor_reembolso NUMERIC(14,2),
            qtd_itens_reembolso INTEGER,
            motivo_reembolso TEXT,
            nf_id INTEGER REFERENCES notas_fiscais(id),
            deletado_em DATETIME
        )
    """

    con = sqlite3.connect(str(DB_PATH))
    con.isolation_level = None  # autocommit — controle manual de transações
    try:
        # Adiciona colunas novas (idempotente — ignora se já existem)
        new_cols = [
            "data_vencimento_original DATE",
            "prorrogada BOOLEAN DEFAULT 0",
            "isento_encargos BOOLEAN",
            "tipo_pgto_prorrogacao VARCHAR(20)",
            "chave_pix VARCHAR(100)",
            "multa_pct NUMERIC(6,2)",
            "juros_diario_pct NUMERIC(6,4)",
            "data_prevista_pagamento DATE",
            "dias_cartorio INTEGER",
            "valor_atualizado NUMERIC(14,2)",
            "sera_reembolsado BOOLEAN DEFAULT 0",
            "valor_reembolso NUMERIC(14,2)",
            "qtd_itens_reembolso INTEGER",
            "motivo_reembolso TEXT",
            "fornecedor VARCHAR(120)",
            "valor_item_total NUMERIC(14,2)",
            "tipo_custo VARCHAR(30)",
            "nf_id INTEGER REFERENCES notas_fiscais(id)",
            "deletado_em DATETIME",
        ]
        for col_def in new_cols:
            try:
                con.execute(f"ALTER TABLE manutencao_parcelas ADD COLUMN {col_def}")
            except Exception:
                pass

        # Recria índices (idempotentes)
        con.execute("CREATE INDEX IF NOT EXISTS idx_parcela_nf ON manutencao_parcelas(nf_id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_parcela_venc ON manutencao_parcelas(data_vencimento)")

        # Verifica se manutencao_id ainda tem NOT NULL
        row = con.execute(
            "SELECT \"notnull\" FROM pragma_table_info('manutencao_parcelas') WHERE name='manutencao_id'"
        ).fetchone()
        if not (row and row[0] == 1):
            return  # já nullable, nada a fazer

        logger.info("Relaxando NOT NULL em manutencao_parcelas.manutencao_id ...")
        con.execute("PRAGMA foreign_keys=OFF")
        con.execute("BEGIN")
        try:
            # Captura colunas da tabela atual (antes de renomear)
            cols_old = [r[1] for r in con.execute("PRAGMA table_info('manutencao_parcelas')").fetchall()]

            # Remove resquício de tentativa anterior, se houver
            con.execute("DROP TABLE IF EXISTS manutencao_parcelas_old")
            con.execute("ALTER TABLE manutencao_parcelas RENAME TO manutencao_parcelas_old")
            con.execute(NEW_TABLE_DDL)

            # Copia apenas colunas que existem em ambas as tabelas
            cols_new = [r[1] for r in con.execute("PRAGMA table_info('manutencao_parcelas')").fetchall()]
            cols_comuns = [c for c in cols_old if c in cols_new]
            col_list = ", ".join(cols_comuns)
            con.execute(
                f"INSERT INTO manutencao_parcelas ({col_list}) "
                f"SELECT {col_list} FROM manutencao_parcelas_old"
            )
            con.execute("DROP TABLE manutencao_parcelas_old")
            con.execute("COMMIT")
            con.execute("CREATE INDEX IF NOT EXISTS idx_parcela_nf ON manutencao_parcelas(nf_id)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_parcela_venc ON manutencao_parcelas(data_vencimento)")
            logger.info("manutencao_parcelas.manutencao_id agora permite NULL")
        except Exception as e:
            con.execute("ROLLBACK")
            logger.error("Erro relaxando NOT NULL em manutencao_parcelas: %s", e)
            raise
        finally:
            con.execute("PRAGMA foreign_keys=ON")
    finally:
        con.close()

# ─────────────────────────────────────────────
# Helpers do novo modelo (OS / NF / parcelas)
# ─────────────────────────────────────────────
def generate_numero_os_atomic(db: Session) -> str:
    """Gera numero_os atomicamente via UPSERT na tabela os_counters.

    Seguro em concorrência (SQLite serializa writes). UNIQUE em
    ordens_servico.numero_os é rede de proteção final.
    """
    from sqlalchemy import text
    from datetime import datetime as _dt
    year = _dt.now().year
    row = db.execute(text("""
        INSERT INTO os_counters (ano, ultimo) VALUES (:y, 1)
        ON CONFLICT(ano) DO UPDATE SET ultimo = os_counters.ultimo + 1
        RETURNING ultimo
    """), {"y": year}).fetchone()
    db.flush()
    numero = row[0] if row else 1
    return f"OS-{year}-{str(numero).zfill(4)}"


def validar_consistencia_os(db: Session, os_id: int) -> list[str]:
    """Retorna lista de erros de consistência financeira (vazia = OK).

    Tolerância: R$ 0,01 (arredondamento).
    """
    erros: list[str] = []
    os = db.get(models.OrdemServico, os_id)
    if not os:
        return [f"OS {os_id} não encontrada"]

    nfs_ativas = [nf for nf in os.notas_fiscais if nf.deletado_em is None]

    # Todos os itens da OS devem estar vinculados a pelo menos uma NF
    os_item_ids_vinculados = {nfi.os_item_id for nf in nfs_ativas for nfi in nf.itens}
    for it in os.itens:
        if it.id not in os_item_ids_vinculados:
            cat = it.categoria or ''
            label = it.servico or it.sistema or f"Item {it.id}"
            erros.append(f"Item '{label}' não vinculado a nenhuma NF")

    for nf in nfs_ativas:
        soma_itens = sum(float(ni.valor_total_item or 0) for ni in nf.itens)
        valor_nf = float(nf.valor_total_nf or 0)
        if soma_itens > 0 and abs(soma_itens - valor_nf) > 0.01:
            erros.append(
                f"NF {nf.numero_nf or nf.id}: soma dos itens ({soma_itens:.2f}) "
                f"≠ valor_total_nf ({valor_nf:.2f})"
            )
        parcelas_ativas = [p for p in nf.parcelas if p.deletado_em is None]
        soma_parcelas = sum(float(p.valor_parcela or 0) for p in parcelas_ativas)
        if parcelas_ativas and abs(soma_parcelas - valor_nf) > 0.01:
            erros.append(
                f"NF {nf.numero_nf or nf.id}: soma das parcelas ({soma_parcelas:.2f}) "
                f"≠ valor_total_nf ({valor_nf:.2f})"
            )

    total_nfs = sum(float(nf.valor_total_nf or 0) for nf in nfs_ativas)
    if os.total_os and abs(total_nfs - float(os.total_os)) > 0.01:
        erros.append(
            f"OS total ({float(os.total_os):.2f}) ≠ soma das NFs ({total_nfs:.2f})"
        )
    return erros


def _infer_tipo_nf(m) -> tuple[str, bool]:
    """Retorna (tipo_nf, needs_review). needs_review=True quando heurística é ambígua."""
    cat = (m.categoria or "").lower()
    if any(k in cat for k in ("compra", "produto", "peça", "peca")):
        return "Produto", False
    if any(k in cat for k in ("serviço", "servico", "mão", "mao")):
        return "Servico", False
    return "Servico", True


def _status_os_from_manutencao(status_manut: str) -> str:
    """Mapeia status_manutencao legado para status_os do novo modelo."""
    mapping = {
        "aberta": "aberta",
        "em_andamento": "em_andamento",
        "aguardando_peca": "aguardando_peca",
        "pendente": "em_andamento",
        "finalizada": "finalizada",
    }
    return mapping.get(status_manut, "em_andamento")


def _migrate_1to1_safe():
    """Migração 1:1 idempotente — cada manutencao vira uma OS com um item.

    Parcelas são agrupadas pela mesma nota (numero_nf, nota) em uma única NF.
    """
    import json
    from database import SessionLocal
    db = SessionLocal()
    try:
        manuts = db.query(models.Manutencao).all()
        usados: set[str] = set(
            x[0] for x in db.query(models.OrdemServico.numero_os)
            .filter(models.OrdemServico.numero_os.isnot(None)).all()
        )
        for m in manuts:
            # Idempotência: pula se já migrado
            existe = (
                db.query(models.OrdemServico)
                .filter(models.OrdemServico.migrado_de_ids.like(f'%[{m.id}]%')
                        | models.OrdemServico.migrado_de_ids.like(f'%[{m.id},%')
                        | models.OrdemServico.migrado_de_ids.like(f'%,{m.id}]%')
                        | models.OrdemServico.migrado_de_ids.like(f'%,{m.id},%'))
                .first()
            )
            if existe:
                continue

            # Desambigua numero_os: se já usado no legado, sufixa com -L{id}
            numero_os = None
            if m.status_manutencao == "finalizada" and m.id_ord_serv:
                candidato = str(m.id_ord_serv).strip() or None
                if candidato:
                    if candidato in usados:
                        candidato = f"{candidato}-L{m.id}"
                    usados.add(candidato)
                    numero_os = candidato

            os = models.OrdemServico(
                numero_os=numero_os,
                status_os=_status_os_from_manutencao(m.status_manutencao or "em_andamento"),
                id_veiculo=m.id_veiculo,
                placa=m.placa,
                modelo=m.modelo,
                empresa=m.empresa,
                id_contrato=m.id_contrato,
                implemento=m.implemento,
                fornecedor=m.fornecedor,
                tipo_manutencao=m.tipo_manutencao,
                categoria=m.categoria,
                total_os=m.total_os,
                responsavel_tec=m.responsavel_tec,
                indisponivel=bool(m.indisponivel),
                km=m.km,
                data_entrada=m.data_entrada,
                data_execucao=m.data_execucao,
                prox_km=m.prox_km,
                prox_data=m.prox_data,
                observacoes=m.observacoes,
                migrado_de_ids=json.dumps([m.id]),
            )
            db.add(os)
            db.flush()

            os_items_map = {}
            if m.parcelas:
                for p in m.parcelas:
                    sys_t = p.sistema_temp or m.sistema
                    srv_t = p.servico_temp or m.servico
                    desc_t = p.descricao_temp or m.descricao
                    k_item = (sys_t, srv_t, desc_t)
                    
                    if k_item not in os_items_map:
                        item = models.OsItem(
                            os_id=os.id,
                            sistema=sys_t,
                            servico=srv_t,
                            descricao=desc_t,
                            qtd_itens=m.qtd_itens,
                            posicao_pneu=m.posicao_pneu,
                            qtd_pneu=m.qtd_pneu,
                            espec_pneu=m.espec_pneu,
                            marca_pneu=m.marca_pneu,
                            manejo_pneu=m.manejo_pneu,
                            manutencao_origem_id=m.id,
                        )
                        db.add(item)
                        db.flush()
                        os_items_map[k_item] = item
            else:
                item = models.OsItem(
                    os_id=os.id,
                    sistema=m.sistema,
                    servico=m.servico,
                    descricao=m.descricao,
                    qtd_itens=m.qtd_itens,
                    posicao_pneu=m.posicao_pneu,
                    qtd_pneu=m.qtd_pneu,
                    espec_pneu=m.espec_pneu,
                    marca_pneu=m.marca_pneu,
                    manejo_pneu=m.manejo_pneu,
                    manutencao_origem_id=m.id,
                )
                db.add(item)
                db.flush()
                os_items_map[(m.sistema, m.servico, m.descricao)] = item

            # Agrupa parcelas pela mesma nota
            grupos: dict = {}
            for p in m.parcelas:
                chave = (p.nf_ordem, p.nota or f"__solo_{p.id}", p.fornecedor, p.empresa_temp)
                grupos.setdefault(chave, []).append(p)

            nfs_criadas = []
            for (nf_ordem, _, _forn, _emp), parcelas_grupo in grupos.items():
                tipo, needs_review = _infer_tipo_nf(m)
                primeira = parcelas_grupo[0]
                valor_nf = (
                    float(primeira.valor_item_total)
                    if primeira.valor_item_total
                    else sum(float(p.valor_parcela or 0) for p in parcelas_grupo)
                )
                nf = models.NotaFiscal(
                    os_id=os.id,
                    numero_nf=primeira.nota,
                    tipo_nf=tipo,
                    tipo_nf_needs_review=needs_review,
                    fornecedor=primeira.fornecedor or m.fornecedor,
                    empresa_faturada=primeira.empresa_temp or m.empresa,
                    valor_total_nf=valor_nf,
                    data_emissao=m.data_execucao,
                    nf_ordem_origem=nf_ordem,
                )
                db.add(nf)
                db.flush()
                nfs_criadas.append(nf)

                item_parcelas = {}
                for p in parcelas_grupo:
                    k_item = (p.sistema_temp or m.sistema, p.servico_temp or m.servico, p.descricao_temp or m.descricao)
                    item_parcelas.setdefault(k_item, []).append(p)

                for k_item, p_list in item_parcelas.items():
                    o_item = os_items_map.get(k_item)
                    primeira_p = p_list[0]
                    valor_nf_item = (
                        float(primeira_p.valor_item_total)
                        if primeira_p.valor_item_total
                        else sum(float(p.valor_parcela or 0) for p in p_list)
                    )
                    nf_item = models.NfItem(
                        nf_id=nf.id,
                        os_item_id=o_item.id if o_item else None,
                        quantidade=1,
                        valor_unitario=valor_nf_item,
                        valor_total_item=valor_nf_item,
                    )
                    db.add(nf_item)

                for p in parcelas_grupo:
                    p.nf_id = nf.id

            empresas = set(nf.empresa_faturada for nf in nfs_criadas if nf.empresa_faturada)
            fornecedores = set(nf.fornecedor for nf in nfs_criadas if nf.fornecedor)
            
            if len(empresas) > 1:
                os.empresa = "Várias"
            elif len(empresas) == 1:
                os.empresa = list(empresas)[0]
                
            if len(fornecedores) > 1:
                os.fornecedor = " / ".join(list(fornecedores))
            elif len(fornecedores) == 1:
                os.fornecedor = list(fornecedores)[0]

            db.commit()
    except Exception as e:
        db.rollback()
        logger.error("[migration 1:1] ERRO: %s", e)
    finally:
        db.close()


import os as _os

_CORS_ORIGINS = _os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

_excel_env = _os.getenv("EXCEL_PATH")
EXCEL_PATH = Path(_excel_env) if _excel_env else Path(__file__).parent.parent / "Locadora.xlsx"

SHEETS = {
    "frota":            "🚛 FROTA",
    "fat_unitario":     "💰 FAT_UNITARIO",
    "reembolsos":       "↩️ REEMBOLSOS",
    "manutencoes":      "🔧 MANUTENCOES",
    "faturamento":      "🧾 FATURAMENTO",
    "seguro_mensal":    "📋 SEGURO_MENSAL",
    "impostos":         "📋 IMPOSTOS",
    "rastreamento":     "📍RASTREAMENTO",
    "contratos":        "📄 CONTRATOS",
    "clientes":         "🏢 CLIENTES",
    "empresas":         "🏢 EMPRESAS",
    "contrato_veiculo": "🔗 CONTRATO_VEICULO",
}

_cache: dict = {}
_cache_mtime: float = 0.0


def load_raw() -> dict:
    global _cache_mtime
    try:
        mtime = EXCEL_PATH.stat().st_mtime
    except OSError:
        mtime = 0.0
    if _cache and mtime == _cache_mtime:
        return _cache
    _cache.clear()
    _cache_mtime = mtime
    with pd.ExcelFile(EXCEL_PATH) as xl:
        for key, name in SHEETS.items():
            try:
                _cache[key] = xl.parse(name)
            except Exception as e:
                logger.warning("Sheet '%s' não encontrada: %s", name, e)
                _cache[key] = pd.DataFrame()
    return _cache


def safe(v):
    try:
        f = float(v)
        return 0.0 if (np.isnan(f) or np.isinf(f)) else round(f, 2)
    except Exception:
        return 0.0


def _empresa_nome(data: dict, empresa_code) -> str | None:
    """Converte código numérico de empresa (ex: '1.0') para RazaoSocial."""
    if empresa_code is None:
        return None
    try:
        eid = int(float(empresa_code))
    except (ValueError, TypeError):
        return str(empresa_code)
    df = data.get("empresas", pd.DataFrame())
    if df.empty or "IDEmpresa" not in df.columns:
        return str(empresa_code)
    row = df[df["IDEmpresa"] == eid]
    if row.empty:
        return str(empresa_code)
    nome = row.iloc[0].get("RazaoSocial")
    return str(nome) if pd.notna(nome) else str(empresa_code)


def _contrato_ativo(data: dict, id_veiculo, data_exec) -> dict | None:
    """Retorna o contrato ativo para um veículo em uma data de execução."""
    if not id_veiculo or not data_exec:
        return None
    try:
        id_veiculo = int(id_veiculo)
        dc = pd.Timestamp(data_exec)
    except Exception:
        return None
    cv  = data.get("contrato_veiculo", pd.DataFrame())
    con = data.get("contratos",        pd.DataFrame())
    if cv.empty or con.empty:
        return None
    ids_contrato = cv[cv["IDVeiculo"] == id_veiculo]["IDContrato"].tolist()
    if not ids_contrato:
        return None
    mask = (
        con["IDContrato"].isin(ids_contrato) &
        (pd.to_datetime(con["DataInicio"], errors="coerce") <= dc) &
        (
            con["DataEncerramento"].isna() |
            (pd.to_datetime(con["DataEncerramento"], errors="coerce") >= dc)
        )
    )
    ativos = con[mask]
    if ativos.empty:
        return None
    row = ativos.iloc[-1]
    return {
        "contrato_nome":   str(row.get("NomeCliente",      "")),
        "contrato_cidade": str(row.get("CidadeOperacao",   "")),
        "contrato_inicio": str(row.get("DataInicio",       ""))[:10] if pd.notna(row.get("DataInicio")) else None,
        "contrato_fim":    str(row.get("DataFimPrevista",  ""))[:10] if pd.notna(row.get("DataFimPrevista")) else None,
        "contrato_status": str(row.get("StatusContrato",   "")),
    }


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

    # ── Excel Notas Count ──────────────────────────────────
    if not manut_raw.empty and "IDOrdServ" in manut_raw.columns and "Nota" in manut_raw.columns:
        # Contagem de notas únicas por OS vindas do Excel
        excel_counts = manut_raw.dropna(subset=["IDOrdServ"]).groupby("IDOrdServ")["Nota"].nunique().rename("qtd_notas_excel")
        manut_raw = manut_raw.merge(excel_counts, on="IDOrdServ", how="left")
    
    # ── Integrar Dados do Banco SQL (Ordens de Serviço e Frota) ──────
    try:
        with engine.connect() as conn:
            # 1. Carregar Veículos da SQL para garantir que placas novas apareçam
            sql_frota = pd.read_sql("SELECT id as IDVeiculo, placa as Placa, marca as Marca, modelo as Modelo, status as Status, tipagem as Tipagem, implemento as Implemento FROM frota", conn)
            if not sql_frota.empty:
                frota = pd.concat([frota, sql_frota], ignore_index=True).drop_duplicates(subset=["Placa"], keep="last")
            
            # 2. Carregar OS Finalizadas do SQL para o ano selecionado
            sql_os = pd.read_sql("""
                SELECT os.id as id_sql, os.id_veiculo as IDVeiculo, os.placa as Placa,
                       COALESCE(os.data_execucao, os.data_entrada) as DataExecução,
                       COALESCE(os.total_os, (SELECT SUM(valor_total_nf) FROM notas_fiscais WHERE os_id = os.id AND deletado_em IS NULL), 0) as TotalOS,
                       os.fornecedor as Fornecedor, os.modelo as Modelo, os.numero_os as IDOrdServ,
                       os.tipo_manutencao as TipoManutencao, os.km as KM, os.prox_km as ProxKM, os.prox_data as ProxData,
                       (SELECT sistema FROM os_itens WHERE os_id = os.id LIMIT 1) as Sistema,
                       (SELECT servico FROM os_itens WHERE os_id = os.id LIMIT 1) as Serviço,
                       (SELECT COUNT(*) FROM notas_fiscais WHERE os_id = os.id AND deletado_em IS NULL) as qtd_notas
                FROM ordens_servico os
                WHERE os.deletado_em IS NULL
                  AND strftime('%Y', COALESCE(os.data_execucao, os.data_entrada)) = :year
            """, conn, params={"year": str(year)})
            
            if not sql_os.empty:
                sql_os["DataExecução"] = pd.to_datetime(sql_os["DataExecução"])
                # Evitar duplicados se por acaso houver IDOrdServ igual (migração)
                if not manut_raw.empty and "IDOrdServ" in manut_raw.columns:
                    os_existentes = set(manut_raw["IDOrdServ"].dropna().unique())
                    sql_os = sql_os[~sql_os["IDOrdServ"].isin(os_existentes)]
                
                manut_raw = pd.concat([manut_raw, sql_os], ignore_index=True)
    except Exception as e:
        logger.error("Erro ao integrar SQL no Dashboard: %s", e)

    # ── Lógica de Reclassificação e Notas ─────────────────
    if not manut_raw.empty:
        # Unifica qtd_notas (SQL vs Excel)
        if "qtd_notas_excel" in manut_raw.columns:
            if "qtd_notas" not in manut_raw.columns:
                manut_raw["qtd_notas"] = manut_raw["qtd_notas_excel"]
            else:
                manut_raw["qtd_notas"] = manut_raw["qtd_notas"].fillna(manut_raw["qtd_notas_excel"])

        def _reclassify(row):
            sistema = str(row.get("Sistema", "")).strip().lower()
            tipo = str(row.get("TipoManutencao", "")).strip().lower()
            servico = str(row.get("Serviço", "")).strip().lower()
            os_id = str(row.get("IDOrdServ", ""))

            is_revisao = False
            # Caso 1: Sistema é 'revisão'
            if sistema == 'revisão':
                row["Sistema"] = "Motor"
                if tipo == 'preventiva':
                    is_revisao = True
            
            # Caso 2: OS 0205 ou contém 'óleo' e é preventiva no motor
            if os_id == 'OS-2026-0205' or ('óleo' in servico):
                if tipo == 'preventiva' and str(row.get("Sistema", "")).lower() == 'motor':
                    is_revisao = True
            
            row["evento"] = "Revisão" if is_revisao else None
            return row

        manut_raw = manut_raw.apply(_reclassify, axis=1)

    manut = _dedup_manut(manut_raw)

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

    base_cols = ["IDVeiculo", "Placa", "Marca", "Modelo", "Status", "Tipagem", "Implemento", "AnoModelo"]
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
    # Also include years from OS records in the DB
    try:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            rows = conn.execute(_text("""
                SELECT DISTINCT CAST(strftime('%Y', data_entrada) AS INTEGER) as yr
                FROM ordens_servico WHERE data_entrada IS NOT NULL
                UNION
                SELECT DISTINCT CAST(strftime('%Y', data_execucao) AS INTEGER) as yr
                FROM ordens_servico WHERE data_execucao IS NOT NULL
            """)).fetchall()
            years.update(r[0] for r in rows if r[0])
    except Exception:
        pass
    return {"years": sorted(years, reverse=True)}


@app.get("/api/kpis")
def get_kpis(year: int = Query(..., ge=2000, le=2100)):
    _, _, kpis, *_ = compute(year)
    return kpis


@app.get("/api/monthly")
def get_monthly(year: int = Query(..., ge=2000, le=2100)):
    _, monthly, *_ = compute(year)
    records = []
    for _, row in monthly.iterrows():
        records.append({k: safe(v) if isinstance(v, (float, int, np.floating)) else str(v) for k, v in row.items()})
    return {"monthly": records}


@app.get("/api/vehicles")
def get_vehicles(year: int = Query(..., ge=2000, le=2100), region: str = Query(None)):
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
            "ano_modelo":         str(row.get("AnoModelo", "")),
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
def get_regions(year: int = Query(..., ge=2000, le=2100)):
    data  = load_raw()
    fat   = _filter_year(_parse(data["fat_unitario"].copy(), "Mes"), "Mes", year)
    if fat.empty or "Contrato" not in fat.columns:
        return {"regions": []}
    regions = sorted(fat["Contrato"].dropna().unique().tolist())
    return {"regions": regions}


@app.get("/api/vehicle/{placa}")
def get_vehicle(placa: str, year: int = Query(..., ge=2000, le=2100)):
    import traceback as _tb
    _empty = {"info": {}, "kpis": {}, "monthly": [], "by_contract": [], "maintenance": []}
    try:
        return _get_vehicle_body(placa, year)
    except Exception:
        logger.error("[get_vehicle] ERRO %s year=%s:\n%s", placa, year, _tb.format_exc())
        return _empty


def _get_vehicle_body(placa: str, year: int):
    df, _, _, fat, reimb, manut, seg, rast, _ = compute(year)

    placa_norm = placa.strip().upper()
    mask = df["Placa"].str.strip().str.upper() == placa_norm
    if not mask.any():
        return {"info": {}, "kpis": {}, "monthly": [], "by_contract": [], "maintenance": []}

    row  = df[mask].iloc[0]
    id_v = row["IDVeiculo"]

    def _s(v):
        """str() seguro: NaN/None → '—'"""
        if v is None:
            return "—"
        try:
            import math
            if isinstance(v, float) and math.isnan(v):
                return "—"
        except Exception:
            pass
        s = str(v)
        return "—" if s.lower() in ("nan", "none", "nat") else s

    info = {
        "placa":      _s(row["Placa"]),
        "marca":      _s(row["Marca"]),
        "modelo":     _s(row["Modelo"]),
        "tipagem":    _s(row.get("Tipagem", "")),
        "implemento": _s(row.get("Implemento", "")),
        "status":     _s(row["Status"]),
        "contrato":   _s(row.get("Contrato", "—")),
        "valor_total": safe(row.get("ValorTotal", 0)),
        "ano_modelo": _s(row.get("AnoModelo", "")),
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
            ev = mrow.get("evento")
            maintenance.append({
                "ordem":     _s(mrow.get("IDOrdServ")) if pd.notna(mrow.get("IDOrdServ")) else "—",
                "data":      str(dt)[:10] if pd.notna(dt) else "—",
                "valor":     safe(mrow.get("TotalOS", 0)),
                "fornecedor": _s(mrow.get("Fornecedor")),
                "sistema":   _s(mrow.get("Sistema")),
                "servico":   _s(mrow.get("Serviço")),
                "tipo":      _s(mrow.get("TipoManutencao")),
                "km":        safe(mrow.get("KM", 0)) if pd.notna(mrow.get("KM")) else None,
                "prox_km":   safe(mrow.get("ProxKM", 0)) if pd.notna(mrow.get("ProxKM")) else None,
                "prox_data": str(mrow.get("ProxData", ""))[:10] if pd.notna(mrow.get("ProxData")) else None,
                "qtd_notas": int(mrow.get("qtd_notas", 0)) if pd.notna(mrow.get("qtd_notas")) else 0,
                "evento":    ev if (ev is not None and pd.notna(ev)) else None,
            })

    return {
        "info":        info,
        "kpis":        kpis_v,
        "monthly":     monthly,
        "by_contract": by_contract,
        "maintenance": sorted(maintenance, key=lambda x: x["data"], reverse=True),
    }


@app.get("/api/maintenance_analysis")
def get_maintenance_analysis(year: int = Query(..., ge=2000, le=2100), placa: str = Query(None)):
    _, _, _, _, _, manut, *_ = compute(year)
    manut_all = manut.copy()

    if placa and not manut.empty and "Placa" in manut.columns:
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


# ═══════════════════════════════════════════════════════════════════
#  CRUD — MANUTENÇÕES (banco SQLite)
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/db/manutencoes", response_model=list[schemas.ManutencaoResponse])
def list_manutencoes(
    status: str = Query(None, description="Filtrar por status_manutencao"),
    placa:  str = Query(None, description="Filtrar por placa"),
    db: Session = Depends(get_db),
):
    """Lista todas as OS. Filtros opcionais: ?status=em_andamento&placa=ABC1234"""
    q = db.query(models.Manutencao)
    if status:
        q = q.filter(models.Manutencao.status_manutencao == status)
    if placa:
        q = q.filter(models.Manutencao.placa == placa.upper())
    return q.order_by(models.Manutencao.criado_em.desc()).all()


@app.get("/api/db/manutencoes/{manutencao_id}", response_model=schemas.ManutencaoResponse)
def get_manutencao(manutencao_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Manutencao, manutencao_id)
    if not obj:
        raise HTTPException(404, "Manutenção não encontrada")
    return obj


@app.post("/api/db/manutencoes", response_model=schemas.ManutencaoResponse, status_code=201)
def abrir_manutencao(payload: schemas.ManutencaoAbrir, db: Session = Depends(get_db)):
    """Abre uma nova OS (veículo entrou em manutenção)."""
    veiculo = db.get(models.Frota, payload.id_veiculo)
    if not veiculo:
        raise HTTPException(404, f"Veículo {payload.id_veiculo} não encontrado na frota")

    obj = models.Manutencao(**payload.model_dump())
    if not obj.placa:
        obj.placa = veiculo.placa
    if not obj.modelo:
        obj.modelo = veiculo.modelo

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.patch("/api/db/manutencoes/{manutencao_id}", response_model=schemas.ManutencaoResponse)
def atualizar_manutencao(
    manutencao_id: int,
    payload: schemas.ManutencaoUpdate,
    db: Session = Depends(get_db),
):
    """Atualiza status ou dados gerais de uma OS em andamento."""
    obj = db.get(models.Manutencao, manutencao_id)
    if not obj:
        raise HTTPException(404, "Manutenção não encontrada")
    if obj.status_manutencao == "finalizada":
        raise HTTPException(400, "OS já finalizada — use o endpoint de finalização para editar dados financeiros")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)

    db.commit()
    db.refresh(obj)
    return obj


@app.post("/api/db/manutencoes/{manutencao_id}/finalizar", response_model=schemas.ManutencaoResponse)
def finalizar_manutencao(
    manutencao_id: int,
    payload: schemas.ManutencaoFinalizar,
    db: Session = Depends(get_db),
):
    """Finaliza a OS (ou reedita uma já finalizada): preenche dados financeiros e recria as parcelas."""
    obj = db.get(models.Manutencao, manutencao_id)
    if not obj:
        raise HTTPException(404, "Manutenção não encontrada")

    # Atualiza campos da OS
    for field in ("id_ord_serv", "total_os", "data_execucao", "empresa", "categoria",
                  "qtd_itens", "prox_km", "prox_data", "km",
                  "posicao_pneu", "qtd_pneu", "espec_pneu", "marca_pneu", "manejo_pneu"):
        val = getattr(payload, field, None)
        if val is not None:
            setattr(obj, field, val)

    obj.status_manutencao = "finalizada"
    obj.indisponivel = False

    # Substitui parcelas (apaga antigas antes de criar novas)
    for parcela_antiga in list(obj.parcelas):
        db.delete(parcela_antiga)
    db.flush()
    for p in payload.parcelas:
        parcela = models.ManutencaoParcela(manutencao_id=obj.id, **p.model_dump())
        db.add(parcela)

    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/api/db/manutencoes/{manutencao_id}", status_code=204)
def deletar_manutencao(manutencao_id: int, db: Session = Depends(get_db)):
    """Remove uma OS."""
    obj = db.get(models.Manutencao, manutencao_id)
    if not obj:
        raise HTTPException(404, "Manutenção não encontrada")
    db.delete(obj)
    db.commit()


# ── Parcelas ─────────────────────────────────────────────────────────

@app.get("/api/db/parcelas", response_model=list[schemas.ParcelaFinanceiroResponse])
def listar_parcelas(year: int = None, db: Session = Depends(get_db)):
    """Retorna parcelas de OS finalizadas (novo ou legado), enriquecidas.

    Prioriza caminho autoritativo parcela → nf → os; fallback para legado manutencao.
    """
    data = load_raw()
    from sqlalchemy import extract, func as sf, or_

    from sqlalchemy.orm import joinedload
    q = (
        db.query(models.ManutencaoParcela)
        .options(
            joinedload(models.ManutencaoParcela.nota_fiscal).joinedload(models.NotaFiscal.os).joinedload(models.OrdemServico.itens),
            joinedload(models.ManutencaoParcela.manutencao)
        )
        .filter(models.ManutencaoParcela.deletado_em.is_(None))
    )
    if year:
        # Robust year extraction for SQLite
        q = q.filter(sf.strftime('%Y', sf.coalesce(
            models.ManutencaoParcela.data_prevista_pagamento,
            models.ManutencaoParcela.data_vencimento
        )) == str(year))
    parcelas = q.order_by(models.ManutencaoParcela.data_vencimento.asc()).all()

    result = []
    for p in parcelas:
        # Determina contexto: preferência pelo novo modelo
        os_obj = None
        manut = None
        if p.nf_id:
            nf = p.nota_fiscal
            if nf and nf.deletado_em is None:
                os_obj = nf.os
        if not os_obj and p.manutencao_id:
            manut = p.manutencao
        if not os_obj and not manut:
            continue

        # Filtra apenas finalizadas (new model) ou manutencao finalizada (legado)
        # (Removido: permitir parcelas de OS em andamento no financeiro)
        # if os_obj and os_obj.status_os != "finalizada":
        #     continue
        # if manut and manut.status_manutencao != "finalizada":
        #     continue

        d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
        if os_obj:
            d["placa"]         = os_obj.placa
            d["modelo"]        = os_obj.modelo
            
            # Normalização de empresa para garantir funcionamento dos filtros no frontend
            emp_val = nf.empresa_faturada or os_obj.empresa
            if str(emp_val).upper() == "TKJ": emp_val = "1"
            elif str(emp_val).upper() == "FINITA": emp_val = "2"
            elif str(emp_val).upper() == "LANDKRAFT": emp_val = "3"
            d["empresa"] = emp_val
            
            d["empresa_nome"]  = _empresa_nome(data, d["empresa"])
            d["id_contrato"]   = os_obj.id_contrato
            d["fornecedor_os"] = os_obj.fornecedor
            d["fornecedor"]    = getattr(p, "fornecedor", None) or nf.fornecedor or os_obj.fornecedor
            # descrição: concatena itens da OS
            d["descricao"]     = "; ".join(filter(None, (it.servico or it.sistema for it in os_obj.itens))) or None
            d["id_ord_serv"]   = os_obj.numero_os
            d["nota"]          = nf.numero_nf  # Garante busca por número de nota
            d["data_execucao"] = os_obj.data_execucao
            contrato = _contrato_ativo(data, os_obj.id_veiculo, os_obj.data_execucao)
        else:
            d["placa"]         = manut.placa
            d["modelo"]        = manut.modelo
            d["empresa"]       = manut.empresa
            d["empresa_nome"]  = _empresa_nome(data, manut.empresa)
            d["id_contrato"]   = manut.id_contrato
            d["fornecedor_os"] = manut.fornecedor
            d["fornecedor"]    = getattr(p, "fornecedor", None) or manut.fornecedor
            d["descricao"]     = manut.descricao
            d["id_ord_serv"]   = manut.id_ord_serv
            d["data_execucao"] = manut.data_execucao
            contrato = _contrato_ativo(data, manut.id_veiculo, manut.data_execucao)

        d["contrato_nome"]   = contrato["contrato_nome"]   if contrato else None
        d["contrato_cidade"] = contrato["contrato_cidade"] if contrato else None
        d["contrato_inicio"] = contrato["contrato_inicio"] if contrato else None
        d["contrato_fim"]    = contrato["contrato_fim"]    if contrato else None
        d["contrato_status"] = contrato["contrato_status"] if contrato else None
        result.append(d)
    return result

@app.post("/api/db/manutencoes/{manutencao_id}/parcelas",
          response_model=schemas.ParcelaResponse, status_code=201)
def adicionar_parcela(
    manutencao_id: int,
    payload: schemas.ParcelaCreate,
    db: Session = Depends(get_db),
):
    obj = db.get(models.Manutencao, manutencao_id)
    if not obj:
        raise HTTPException(404, "Manutenção não encontrada")
    parcela = models.ManutencaoParcela(manutencao_id=manutencao_id, **payload.model_dump())
    db.add(parcela)
    db.commit()
    db.refresh(parcela)
    return parcela


@app.patch("/api/db/parcelas/{parcela_id}", response_model=schemas.ParcelaResponse)
def atualizar_parcela(
    parcela_id: int,
    payload: schemas.ParcelaUpdate,
    db: Session = Depends(get_db),
):
    parcela = db.get(models.ManutencaoParcela, parcela_id)
    if not parcela:
        raise HTTPException(404, "Parcela não encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(parcela, field, value)
    db.commit()
    db.refresh(parcela)
    return parcela


# ── Frota (para preencher selects no frontend) ────────────────────────

@app.get("/api/db/frota", response_model=list[schemas.FrotaResponse])
def listar_frota_db(db: Session = Depends(get_db)):
    ids_ativos = db.query(models.FatUnitario.id_veiculo).distinct().scalar_subquery()
    return (
        db.query(models.Frota)
        .filter(models.Frota.status.in_(["Frota", "Sublocado"]))
        .filter(models.Frota.id.in_(ids_ativos))
        .order_by(models.Frota.placa)
        .all()
    )


# ═════════════════════════════════════════════════════════════════════
# NOVO MODELO: OS → Itens → NFs → Itens da NF → Parcelas
# ═════════════════════════════════════════════════════════════════════

# ── Ordens de Serviço ────────────────────────────────────────────────

@app.get("/api/db/os", response_model=list[schemas.OsResponse])
def list_os(
    status: str = Query(None, description="Filtrar por status_os"),
    placa:  str = Query(None, description="Filtrar por placa"),
    db: Session = Depends(get_db),
):
    q = (
        db.query(models.OrdemServico)
        .options(
            selectinload(models.OrdemServico.itens),
            selectinload(models.OrdemServico.notas_fiscais)
            .selectinload(models.NotaFiscal.parcelas),
        )
        .filter(models.OrdemServico.deletado_em.is_(None))
    )
    if status:
        q = q.filter(models.OrdemServico.status_os == status)
    if placa:
        q = q.filter(models.OrdemServico.placa == placa.upper())
    return q.order_by(models.OrdemServico.criado_em.desc()).all()


@app.get("/api/db/os/{os_id}", response_model=schemas.OsResponse)
def get_os(os_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.OrdemServico, os_id)
    if not obj or obj.deletado_em is not None:
        raise HTTPException(404, "OS não encontrada")
    return obj


@app.post("/api/db/os", response_model=schemas.OsResponse, status_code=201)
def abrir_os(payload: schemas.OsAbrir, db: Session = Depends(get_db)):
    veiculo = db.get(models.Frota, payload.id_veiculo)
    if not veiculo:
        raise HTTPException(404, f"Veículo {payload.id_veiculo} não encontrado")

    data = payload.model_dump(exclude={"itens"})
    if not data.get("modelo"):
        data["modelo"] = veiculo.modelo
    if not data.get("placa"):
        data["placa"] = veiculo.placa

    data["numero_os"] = generate_numero_os_atomic(db)
    
    os = models.OrdemServico(**data)
    db.add(os)
    db.flush()

    for it in payload.itens:
        item = models.OsItem(os_id=os.id, **it.model_dump())
        db.add(item)

    db.commit()
    db.refresh(os)
    return os


@app.patch("/api/db/os/{os_id}", response_model=schemas.OsResponse)
def atualizar_os(os_id: int, payload: schemas.OsUpdate, db: Session = Depends(get_db)):
    os = db.get(models.OrdemServico, os_id)
    if not os or os.deletado_em is not None:
        raise HTTPException(404, "OS não encontrada")
    if os.status_os == "finalizada":
        raise HTTPException(400, "OS finalizada — use endpoints financeiros para edição")

    data = payload.model_dump(exclude_unset=True)
    novos_itens = data.pop("itens", None)

    for field, value in data.items():
        setattr(os, field, value)

    # Substituir itens: lógica inteligente para evitar quebra de FK
    if novos_itens is not None:
        item_map = {it.id: it for it in os.itens}
        incoming_ids = {it.get("id") for it in novos_itens if it.get("id") is not None}

        # 1. Update or Add
        for it_data in novos_itens:
            iid = it_data.pop("id", None)
            if iid and iid in item_map:
                target = item_map[iid]
                for k, v in it_data.items():
                    if hasattr(target, k):
                        setattr(target, k, v)
            else:
                db.add(models.OsItem(os_id=os.id, **it_data))

        # 2. Delete missing items (apenas se não houver vínculos impeditivos, ou confia no erro controlado)
        for iid, it in item_map.items():
            if iid not in incoming_ids:
                db.delete(it)

    db.commit()
    db.refresh(os)
    return os


@app.patch("/api/db/os/{os_id}/editar", response_model=schemas.OsResponse)
def editar_os_finalizada(os_id: int, payload: schemas.OsEditarFinalizada, db: Session = Depends(get_db)):
    """Edição de campos de execução e itens de uma OS finalizada."""
    try:
        # Explicitamente carregar as relações para evitar problemas de lazy-loading
        os = db.query(models.OrdemServico).options(
            selectinload(models.OrdemServico.itens),
            selectinload(models.OrdemServico.notas_fiscais)
        ).filter(models.OrdemServico.id == os_id).first()

        if not os or os.deletado_em is not None:
            raise HTTPException(404, "OS não encontrada")

        data = payload.model_dump(exclude_unset=True)
        novos_itens = data.pop("itens", None)

        # Campos permitidos para atualização direta no cabeçalho da OS
        for field, value in data.items():
            if hasattr(os, field):
                setattr(os, field, value)

        if novos_itens is not None:
            item_map = {it.id: it for it in os.itens}
            incoming_ids = {it.get("id") for it in novos_itens if it.get("id") is not None}

            # 1. Update or Add
            for it_data in novos_itens:
                # it_data já é um dict pois veio de payload.model_dump()
                iid = it_data.pop("id", None)
                if iid and iid in item_map:
                    # Update existing item
                    target = item_map[iid]
                    for k, v in it_data.items():
                        if hasattr(target, k):
                            setattr(target, k, v)
                else:
                    # Add new item
                    db.add(models.OsItem(os_id=os.id, **it_data))

            # 2. Delete missing items
            for iid, it in item_map.items():
                if iid not in incoming_ids:
                    # Check if referenced in nf_itens
                    is_referenced = db.query(models.NfItem).filter(models.NfItem.os_item_id == iid).first()
                    if is_referenced:
                        label = it.servico or it.sistema or f"Item #{iid}"
                        raise HTTPException(400, f"O item '{label}' não pode ser excluído porque já está vinculado a uma Nota Fiscal. Remova o vínculo na NF primeiro.")
                    db.delete(it)

        db.commit()
        db.refresh(os)
        return os
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(400, f"Erro interno ao salvar OS: {str(e)}")


@app.delete("/api/db/os/{os_id}", status_code=204)
def deletar_os(os_id: int, db: Session = Depends(get_db)):
    """Soft delete em cascata para OS, NFs e Parcelas."""
    from datetime import datetime as _dt
    os = db.get(models.OrdemServico, os_id)
    if not os or os.deletado_em is not None:
        raise HTTPException(404, "OS não encontrada")

    agora = _dt.utcnow()
    os.deletado_em = agora

    for nf in os.notas_fiscais:
        if nf.deletado_em is None:
            nf.deletado_em = agora
            for p in nf.parcelas:
                if p.deletado_em is None:
                    p.deletado_em = agora

    db.commit()


@app.get("/api/db/os/{os_id}/validacao", response_model=list[str])
def validar_os(os_id: int, db: Session = Depends(get_db)):
    return validar_consistencia_os(db, os_id)


@app.post("/api/db/os/{os_id}/executar", response_model=schemas.OsResponse)
def executar_os(os_id: int, payload: schemas.OsExecutar, db: Session = Depends(get_db)):
    """Marca OS como executada (aguardando NF)."""
    os = db.get(models.OrdemServico, os_id)
    if not os or os.deletado_em is not None:
        raise HTTPException(404, "OS não encontrada")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(os, field, value)
    os.status_os = "executado_aguardando_nf"
    db.commit()
    db.refresh(os)
    return os


@app.post("/api/db/os/{os_id}/finalizar", response_model=schemas.OsResponse)
def finalizar_os(os_id: int, db: Session = Depends(get_db)):
    """Finaliza OS. Retorna 422 se inconsistência financeira."""
    os = db.get(models.OrdemServico, os_id)
    if not os or os.deletado_em is not None:
        raise HTTPException(404, "OS não encontrada")

    nfs_ativas = [nf for nf in os.notas_fiscais if nf.deletado_em is None]
    if not nfs_ativas:
        raise HTTPException(400, "OS não possui NFs — lance ao menos uma NF antes de finalizar")

    # Computa total_os como soma das NFs
    os.total_os = sum(float(nf.valor_total_nf or 0) for nf in nfs_ativas)

    erros = validar_consistencia_os(db, os_id)
    if erros:
        raise HTTPException(422, {"erros": erros})

    os.status_os = "finalizada"
    os.indisponivel = False
    db.commit()
    db.refresh(os)
    return os


# ── Itens da OS ──────────────────────────────────────────────────────

@app.post("/api/db/os/{os_id}/itens", response_model=schemas.OsItemResponse, status_code=201)
def adicionar_os_item(os_id: int, payload: schemas.OsItemCreate, db: Session = Depends(get_db)):
    os = db.get(models.OrdemServico, os_id)
    if not os or os.deletado_em is not None:
        raise HTTPException(404, "OS não encontrada")
    item = models.OsItem(os_id=os_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.patch("/api/db/os/{os_id}/itens/{item_id}", response_model=schemas.OsItemResponse)
def atualizar_os_item(os_id: int, item_id: int, payload: schemas.OsItemUpdate, db: Session = Depends(get_db)):
    item = db.get(models.OsItem, item_id)
    if not item or item.os_id != os_id:
        raise HTTPException(404, "Item não encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@app.delete("/api/db/os/{os_id}/itens/{item_id}", status_code=204)
def deletar_os_item(os_id: int, item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.OsItem, item_id)
    if not item or item.os_id != os_id:
        raise HTTPException(404, "Item não encontrado")
    if item.nf_itens:
        raise HTTPException(400, "Item vinculado a NF — remova o vínculo antes")
    db.delete(item)
    db.commit()


# ── NFs ──────────────────────────────────────────────────────────────

@app.get("/api/db/os/{os_id}/nfs", response_model=list[schemas.NotaFiscalResponse])
def listar_nfs(os_id: int, db: Session = Depends(get_db)):
    os = db.get(models.OrdemServico, os_id)
    if not os:
        raise HTTPException(404, "OS não encontrada")
    return [nf for nf in os.notas_fiscais if nf.deletado_em is None]


@app.post("/api/db/os/{os_id}/nfs", response_model=schemas.NotaFiscalResponse, status_code=201)
def adicionar_nf(os_id: int, payload: schemas.NotaFiscalCreate, db: Session = Depends(get_db)):
    os = db.get(models.OrdemServico, os_id)
    if not os or os.deletado_em is not None:
        raise HTTPException(404, "OS não encontrada")

    # Gera numero_os atomicamente na 1ª NF
    if os.numero_os is None:
        os.numero_os = generate_numero_os_atomic(db)

    nf_data = payload.model_dump(exclude={"itens", "parcelas"})
    nf = models.NotaFiscal(os_id=os_id, **nf_data)
    db.add(nf)
    db.flush()

    for it in payload.itens:
        nf_item = models.NfItem(nf_id=nf.id, **it.model_dump())
        db.add(nf_item)

    for p in payload.parcelas:
        parcela = models.ManutencaoParcela(nf_id=nf.id, fornecedor=nf.fornecedor, **p.model_dump())
        db.add(parcela)

    db.commit()
    db.refresh(nf)
    return nf


@app.put("/api/db/os/{os_id}/nfs-sync", response_model=list[schemas.NotaFiscalResponse])
def sync_nfs(os_id: int, payload: list[schemas.NotaFiscalCreate], db: Session = Depends(get_db)):
    """Substitui a lista inteira de Notas Fiscais da OS (sync destrutivo/recreativo)."""
    os_obj = db.get(models.OrdemServico, os_id)
    if not os_obj or os_obj.deletado_em is not None:
        raise HTTPException(404, "OS não encontrada")

    # Verifica se existem parcelas pagas, para bloquear exclusão
    for old_nf in os_obj.notas_fiscais:
        if old_nf.deletado_em is None:
            for p in old_nf.parcelas:
                if p.status_pagamento == "Pago":
                    raise HTTPException(400, "A OS possui parcelas já pagas e não pode ter suas NFs recriadas.")

    # Hard delete das notas antigas (estamos em modo rascunho de finalização)
    for old_nf in list(os_obj.notas_fiscais):
        db.delete(old_nf)
    db.flush()

    if os_obj.numero_os is None and payload:
        os_obj.numero_os = generate_numero_os_atomic(db)

    nfs_criadas = []
    for nf_data in payload:
        data = nf_data.model_dump(exclude={"itens", "parcelas"})
        nf = models.NotaFiscal(os_id=os_id, **data)
        db.add(nf)
        db.flush()

        for it in nf_data.itens:
            db.add(models.NfItem(nf_id=nf.id, **it.model_dump()))
        
        for p in nf_data.parcelas:
            db.add(models.ManutencaoParcela(
                nf_id=nf.id, 
                fornecedor=nf.fornecedor, 
                **p.model_dump()
            ))
            
        nfs_criadas.append(nf)

    db.commit()
    for nf in nfs_criadas:
        db.refresh(nf)
    return nfs_criadas


@app.patch("/api/db/nfs/{nf_id}", response_model=schemas.NotaFiscalResponse)
def atualizar_nf(nf_id: int, payload: schemas.NotaFiscalUpdate, db: Session = Depends(get_db)):
    nf = db.get(models.NotaFiscal, nf_id)
    if not nf or nf.deletado_em is not None:
        raise HTTPException(404, "NF não encontrada")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(nf, field, value)
    db.commit()
    db.refresh(nf)
    return nf


@app.delete("/api/db/nfs/{nf_id}", status_code=204)
def deletar_nf(nf_id: int, db: Session = Depends(get_db)):
    """Soft delete. Bloqueado se houver parcela paga."""
    from datetime import datetime as _dt
    nf = db.get(models.NotaFiscal, nf_id)
    if not nf or nf.deletado_em is not None:
        raise HTTPException(404, "NF não encontrada")
    for p in nf.parcelas:
        if p.deletado_em is None and (p.status_pagamento or "").lower() == "pago":
            raise HTTPException(400, "NF com parcela paga — não pode ser removida")
    nf.deletado_em = _dt.utcnow()
    # Soft delete também nas parcelas ativas
    for p in nf.parcelas:
        if p.deletado_em is None:
            p.deletado_em = _dt.utcnow()
    db.commit()


# ── Itens da NF ──────────────────────────────────────────────────────

@app.post("/api/db/nfs/{nf_id}/itens", response_model=schemas.NfItemResponse, status_code=201)
def adicionar_nf_item(nf_id: int, payload: schemas.NfItemCreate, db: Session = Depends(get_db)):
    nf = db.get(models.NotaFiscal, nf_id)
    if not nf or nf.deletado_em is not None:
        raise HTTPException(404, "NF não encontrada")
    os_item = db.get(models.OsItem, payload.os_item_id)
    if not os_item or os_item.os_id != nf.os_id:
        raise HTTPException(400, "os_item_id não pertence à OS desta NF")
    item = models.NfItem(nf_id=nf_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.patch("/api/db/nfs/{nf_id}/itens/{item_id}", response_model=schemas.NfItemResponse)
def atualizar_nf_item(nf_id: int, item_id: int, payload: schemas.NfItemUpdate, db: Session = Depends(get_db)):
    item = db.get(models.NfItem, item_id)
    if not item or item.nf_id != nf_id:
        raise HTTPException(404, "Item de NF não encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@app.delete("/api/db/nfs/{nf_id}/itens/{item_id}", status_code=204)
def deletar_nf_item(nf_id: int, item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.NfItem, item_id)
    if not item or item.nf_id != nf_id:
        raise HTTPException(404, "Item de NF não encontrado")
    db.delete(item)
    db.commit()


# ── Parcelas vinculadas a NF (novo fluxo) ────────────────────────────

@app.post("/api/db/nfs/{nf_id}/parcelas", response_model=schemas.ParcelaResponse, status_code=201)
def adicionar_parcela_nf(nf_id: int, payload: schemas.ParcelaCreate, db: Session = Depends(get_db)):
    nf = db.get(models.NotaFiscal, nf_id)
    if not nf or nf.deletado_em is not None:
        raise HTTPException(404, "NF não encontrada")
    parcela = models.ManutencaoParcela(nf_id=nf_id, **payload.model_dump())
    db.add(parcela)
    db.commit()
    db.refresh(parcela)
    return parcela


# ── Merge assistido ──────────────────────────────────────────────────

@app.get("/api/db/os/merge-sugestoes", response_model=list[schemas.MergeSugestao])
def merge_sugestoes(db: Session = Depends(get_db)):
    """Sugestões de OS candidatas a merge. Usuário confirma caso-a-caso."""
    from datetime import timedelta
    oss = (
        db.query(models.OrdemServico)
        .filter(models.OrdemServico.deletado_em.is_(None))
        .filter(models.OrdemServico.status_os != "finalizada")
        .all()
    )
    sugestoes = []
    vistos: set[int] = set()

    # Agrupa por id_veiculo + fornecedor + janela de 3 dias
    for i, os_a in enumerate(oss):
        if os_a.id in vistos:
            continue
        grupo = [os_a]
        for os_b in oss[i + 1:]:
            if os_b.id in vistos:
                continue
            if os_b.id_veiculo != os_a.id_veiculo:
                continue
            if (os_a.fornecedor or "") != (os_b.fornecedor or ""):
                continue
            # janela de data_execucao ou data_entrada
            data_a = os_a.data_execucao or os_a.data_entrada
            data_b = os_b.data_execucao or os_b.data_entrada
            if data_a and data_b:
                if abs((data_a - data_b).days) > 3:
                    continue
            grupo.append(os_b)

        if len(grupo) >= 2:
            motivos = ["mesmo veículo", "mesmo fornecedor", "datas próximas (±3 dias)"]
            sugestoes.append(schemas.MergeSugestao(
                os_ids=[o.id for o in grupo],
                placa=os_a.placa,
                fornecedor=os_a.fornecedor,
                id_ord_serv=os_a.numero_os,
                data_execucao=os_a.data_execucao,
                total_itens=sum(len(o.itens) for o in grupo),
                total_nfs=sum(len([nf for nf in o.notas_fiscais if nf.deletado_em is None]) for o in grupo),
                motivos=motivos,
            ))
            for o in grupo:
                vistos.add(o.id)
    return sugestoes


@app.post("/api/db/os/merge", response_model=schemas.OsResponse)
def merge_os(payload: schemas.MergeRequest, db: Session = Depends(get_db)):
    import json
    if payload.os_destino_id not in payload.os_ids:
        raise HTTPException(400, "os_destino_id deve estar em os_ids")

    destino = db.get(models.OrdemServico, payload.os_destino_id)
    if not destino or destino.deletado_em is not None:
        raise HTTPException(404, "OS destino não encontrada")

    origens = [
        db.get(models.OrdemServico, oid)
        for oid in payload.os_ids if oid != payload.os_destino_id
    ]
    for o in origens:
        if not o or o.deletado_em is not None:
            raise HTTPException(404, "Uma das OS origem não encontrada")
        if o.id_veiculo != destino.id_veiculo:
            raise HTTPException(400, "Veículos divergentes entre OS")
        if (o.fornecedor or "") != (destino.fornecedor or ""):
            raise HTTPException(400, "Fornecedores divergentes entre OS")

    # Acumula ids absorvidos
    ids_absorvidos = json.loads(destino.migrado_de_ids or "[]")
    for o in origens:
        ids_absorvidos.extend(json.loads(o.migrado_de_ids or f"[{o.id}]"))
        for item in list(o.itens):
            item.os_id = destino.id
        for nf in list(o.notas_fiscais):
            nf.os_id = destino.id

    destino.migrado_de_ids = json.dumps(sorted(set(ids_absorvidos)))
    db.flush()
    from datetime import datetime as _dt
    for o in origens:
        o.deletado_em = _dt.utcnow()
    db.commit()
    db.refresh(destino)
    return destino


# ── Auditoria / Integridade ──────────────────────────────────────────

@app.get("/api/db/parcelas/integridade", response_model=schemas.IntegridadeResponse)
def integridade_parcelas(db: Session = Depends(get_db)):
    """Retorna parcelas órfãs (sem nf_id) — devem ser zero após migração."""
    total = db.query(models.ManutencaoParcela).count()
    orfas = (
        db.query(models.ManutencaoParcela.id)
        .filter(models.ManutencaoParcela.nf_id.is_(None))
        .filter(models.ManutencaoParcela.deletado_em.is_(None))
        .all()
    )
    return {"orfas": [o[0] for o in orfas], "total": total}
