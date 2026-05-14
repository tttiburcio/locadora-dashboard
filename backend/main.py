from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import text
import pandas as pd
import numpy as np
from pathlib import Path
import io
import logging
import requests as _requests
import threading

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

MAPWS_BASE = "http://localhost:8001"


def _resolve_fornecedor_id(db: Session, name: str | None) -> int | None:
    """Busca id na tabela física fornecedores pelo nome (case-insensitive)."""
    if not name or not str(name).strip():
        return None
    try:
        q = text("SELECT id FROM fornecedores WHERE UPPER(TRIM(nome)) = :n LIMIT 1")
        res = db.execute(q, {"n": str(name).strip().upper()}).fetchone()
        return res[0] if res else None
    except Exception as e:
        logger.warning("Falha ao resolver fornecedor_id para '%s': %s", name, e)
        return None


def _mapws_km_direct(placa: str, date_str: str) -> float | None:
    """Busca odômetro no MAPWS para a placa na data (YYYY-MM-DD). Retorna km_fim ou None."""
    try:
        resp = _requests.get(
            f"{MAPWS_BASE}/api/details/{placa}",
            params={"start_date": date_str, "end_date": date_str},
            timeout=4,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        records = data if isinstance(data, list) else (data.get("data") or data.get("records") or [])
        if not records:
            return None
        rec = records[-1] if isinstance(records, list) else records
        val = rec.get("km_fim") or rec.get("km_acumulado") or rec.get("odometro")
        return float(val) if val is not None else None
    except Exception:
        return None


def _enrich_km_from_mapws():
    """Preenche ordens_servico.km nulo consultando o MAPWS pelo odômetro na data do serviço."""
    import sqlite3
    from database import DB_PATH

    try:
        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute("""
            SELECT id, placa, COALESCE(data_execucao, data_entrada) AS data_exec
            FROM ordens_servico
            WHERE km IS NULL
              AND COALESCE(data_execucao, data_entrada) IS NOT NULL
              AND deletado_em IS NULL
        """).fetchall()

        updated = 0
        for os_id, placa, data_exec in rows:
            date_str   = str(data_exec)[:10]
            placa_norm = str(placa).replace("-", "").strip().upper()
            km_val     = _mapws_km_direct(placa_norm, date_str)
            if km_val is not None:
                conn.execute("UPDATE ordens_servico SET km = ? WHERE id = ?", (km_val, os_id))
                updated += 1

        conn.commit()
        conn.close()
        logger.info("KM enrichment concluído: %d/%d OS atualizadas via MAPWS", updated, len(rows))
    except Exception as e:
        logger.error("Erro em _enrich_km_from_mapws: %s", e)


def _sv_str(v) -> str | None:
    """Converte valor pandas para str, retorna None se nulo/vazio."""
    if v is None:
        return None
    if isinstance(v, float) and (pd.isna(v)):
        return None
    s = str(v).strip()
    return s if s and s.lower() not in ("nan", "none", "nat") else None


def _sv_float(v) -> float | None:
    try:
        f = float(v)
        return None if pd.isna(f) else f
    except Exception:
        return None


def _sv_int(v) -> int | None:
    f = _sv_float(v)
    return int(f) if f is not None else None


def _sv_date(v):
    if v is None:
        return None
    try:
        ts = pd.Timestamp(v)
        return None if pd.isna(ts) else ts.date()
    except Exception:
        return None


def sync_excel_to_db() -> int:
    """Importa do Excel MANUTENCOES → ordens_servico/os_itens os IDOrdServ ausentes no banco.

    Idempotente: pula OS cujo numero_os já existe em ordens_servico.
    Retorna o número de OS importadas.
    """
    from database import SessionLocal
    raw = load_raw()
    manut = raw.get("manutencoes", pd.DataFrame())
    frota_df = raw.get("frota", pd.DataFrame())

    if manut.empty or "IDOrdServ" not in manut.columns:
        return 0

    db = SessionLocal()
    try:
        existing_os: set[str] = set(
            x[0] for x in db.query(models.OrdemServico.numero_os)
            .filter(models.OrdemServico.numero_os.isnot(None)).all()
        )

        col_serv  = _col_like(manut, "servi") or "Serviço"
        col_pos   = _col_like(manut, "posi",    "pneu")
        col_espec = _col_like(manut, "especif", "pneu")
        col_data  = _col_like(manut, "data", "exec") or "DataExecução"

        imported = 0
        for raw_id, grp in manut.dropna(subset=["IDOrdServ"]).groupby("IDOrdServ"):
            id_ord = _sv_str(raw_id)
            if not id_ord or id_ord in existing_os:
                continue

            first = grp.iloc[0]

            id_veiculo = _sv_int(first.get("IDVeiculo"))
            if id_veiculo is None:
                continue

            # Placa via frota lookup
            placa = None
            if not frota_df.empty and "IDVeiculo" in frota_df.columns and "Placa" in frota_df.columns:
                fr = frota_df[frota_df["IDVeiculo"] == id_veiculo]
                if not fr.empty:
                    placa = _sv_str(fr.iloc[0].get("Placa"))

            os_obj = models.OrdemServico(
                numero_os      = id_ord,
                status_os      = "finalizada",
                id_veiculo     = id_veiculo,
                placa          = placa or _sv_str(first.get("Placa")),
                data_execucao  = _sv_date(first.get(col_data)),
                km             = _sv_int(first.get("KM")),
                total_os       = _sv_float(first.get("TotalOS")),
                categoria      = _sv_str(first.get("Categoria")),
                fornecedor     = _sv_str(first.get("Fornecedor")),
                tipo_manutencao= _sv_str(first.get("TipoManutencao")),
                migrado_de_ids = '["excel_sync"]',
            )
            db.add(os_obj)
            db.flush()

            # Itens: um por combinação única (sistema, serviço, posição)
            seen_items: set = set()
            for _, row in grp.iterrows():
                sistema = _sv_str(row.get("Sistema"))
                servico = _sv_str(row.get(col_serv)) if col_serv else None
                posicao = _sv_str(row.get(col_pos))  if col_pos  else None
                espec   = _sv_str(row.get(col_espec)) if col_espec else None
                cat     = _sv_str(row.get("Categoria"))

                key = (sistema, servico, posicao, espec)
                if key in seen_items:
                    continue
                seen_items.add(key)

                db.add(models.OsItem(
                    os_id        = os_obj.id,
                    categoria    = cat,
                    sistema      = sistema,
                    servico      = servico,
                    posicao_pneu = posicao,
                    qtd_pneu     = _sv_int(row.get("QtdPneu")),
                    espec_pneu   = espec,
                    marca_pneu    = _sv_str(row.get("MarcaPneu")),
                    modelo_pneu   = _sv_str(row.get("ModeloPneu")),
                    condicao_pneu = _sv_str(row.get("CondicaoPneu")),
                    manejo_pneu   = _sv_str(row.get("ManejoPneu")),
                ))

            db.commit()
            existing_os.add(id_ord)
            imported += 1

        return imported
    except Exception as e:
        db.rollback()
        logger.error("sync_excel_to_db error: %s", e)
        return 0
    finally:
        db.close()


def sync_db_to_excel() -> int:
    """Acrescenta na planilha MANUTENCOES as OS finalizadas do banco ausentes no Excel.

    Usa o mesmo formato de linha que _sync_os_to_excel (uma linha por NF/parcela).
    OS sem NFs registradas escrevem uma linha de resumo sem dados financeiros.
    Retorna o número de linhas acrescentadas.
    """
    if not EXCEL_PATH.exists():
        return 0

    raw = load_raw()
    manut_excel = raw.get("manutencoes", pd.DataFrame())
    excel_ids: set[str] = set()
    if not manut_excel.empty and "IDOrdServ" in manut_excel.columns:
        excel_ids = set(manut_excel["IDOrdServ"].dropna().astype(str).unique())

    db = SessionLocal()
    try:
        os_list = (
            db.query(models.OrdemServico)
            .filter(
                models.OrdemServico.status_os == "finalizada",
                models.OrdemServico.deletado_em.is_(None),
                models.OrdemServico.numero_os.isnot(None),
            )
            .all()
        )
        new_os = [o for o in os_list if o.numero_os not in excel_ids]
        if not new_os:
            return 0

        # Lê arquivo uma vez; detecta sheet name
        try:
            with pd.ExcelFile(EXCEL_PATH) as xl:
                sheet_name = next((s for s in xl.sheet_names if "manutencao" in s.lower().replace("ç","c").replace("ã","a")), None)
                if not sheet_name:
                    sheet_name = SHEETS["manutencoes"]
                if sheet_name not in xl.sheet_names:
                    return 0
                df = xl.parse(sheet_name)
        except PermissionError:
            logger.warning("sync_db_to_excel: Excel aberto por outro processo — ignorado")
            return 0
        except Exception as e:
            logger.error("sync_db_to_excel leitura: %s", e)
            return 0

        next_id = 1
        if not df.empty and "IDManutencao" in df.columns:
            valid_ids = pd.to_numeric(df["IDManutencao"], errors="coerce").dropna()
            if not valid_ids.empty:
                next_id = int(valid_ids.max()) + 1

        all_new_rows: list[dict] = []
        for os_obj in new_os:
            first_item = os_obj.itens[0] if os_obj.itens else None
            nfs_ativas  = [nf for nf in os_obj.notas_fiscais if nf.deletado_em is None]

            if nfs_ativas:
                for nf in nfs_ativas:
                    # Agrupar peso por sistema para o caso de múltiplos itens do mesmo sistema na mesma NF
                    total_items_cost = sum(float(it.valor_total_item or 0) for it in nf.itens) if getattr(nf, 'itens', None) else 0
                    sys_info = {}
                    if total_items_cost > 0 and len(nf.itens) > 1:
                        for it in nf.itens:
                            sn = (it.os_item.sistema if it.os_item else None) or "Outros"
                            if sn not in sys_info:
                                sys_info[sn] = {"cost": 0.0, "item_ref": it}
                            sys_info[sn]["cost"] += float(it.valor_total_item or 0)
                    
                    for p in [px for px in nf.parcelas if px.deletado_em is None]:
                        # Se houver repartição por sistema calculada
                        if sys_info:
                            for sname, sdict in sys_info.items():
                                ratio = sdict["cost"] / total_items_cost
                                it_ref = sdict["item_ref"]
                                row_val = float(p.valor_parcela) if p.valor_parcela else 0.0
                                
                                all_new_rows.append({
                                    "IDManutencao":       next_id,
                                    "IDOrdServ":          os_obj.numero_os,
                                    "TotalOS":            float(os_obj.total_os) if os_obj.total_os else np.nan,
                                    "Empresa":            os_obj.empresa,
                                    "Placa":              os_obj.placa,
                                    "IDVeiculo":          os_obj.id_veiculo,
                                    "Modelo":             os_obj.modelo,
                                    "Implemento":         os_obj.implemento,
                                    "Fornecedor":         nf.fornecedor or os_obj.fornecedor,
                                    "Nota":               nf.numero_nf,
                                    "Data Venc.":         pd.to_datetime(p.data_vencimento).strftime("%Y-%m-%d") if p.data_vencimento else np.nan,
                                    "ParcelaAtual":       p.parcela_atual,
                                    "ParcelaTotal":       p.parcela_total,
                                    "ValorParcela":       round(row_val * ratio, 2),
                                    "FormaPgto":          p.forma_pgto,
                                    "Categoria":          nf.tipo_nf or os_obj.categoria,
                                    "Status":             p.status_pagamento,
                                    "TipoManutencao":     os_obj.tipo_manutencao,
                                    "Sistema":            sname,
                                    "Serviço":            it_ref.os_item.servico if (it_ref and it_ref.os_item) else np.nan,
                                    "KM":                 float(os_obj.km) if os_obj.km else np.nan,
                                    "DataExecução":       pd.to_datetime(os_obj.data_execucao or os_obj.data_entrada).strftime("%Y-%m-%d") if (os_obj.data_execucao or os_obj.data_entrada) else np.nan,
                                    "PosiçãoPneu":        it_ref.os_item.posicao_pneu if (it_ref and it_ref.os_item) else np.nan,
                                    "QtdPneu":            it_ref.os_item.qtd_pneu if (it_ref and it_ref.os_item) else np.nan,
                                    "EspecificaçãoPneu":  it_ref.os_item.espec_pneu if (it_ref and it_ref.os_item) else np.nan,
                                    "MarcaPneu":          it_ref.os_item.marca_pneu    if (it_ref and it_ref.os_item) else np.nan,
                                    "ModeloPneu":         it_ref.os_item.modelo_pneu   if (it_ref and it_ref.os_item) else np.nan,
                                    "CondicaoPneu":       it_ref.os_item.condicao_pneu if (it_ref and it_ref.os_item) else np.nan,
                                    "ManejoPneu":         it_ref.os_item.manejo_pneu   if (it_ref and it_ref.os_item) else np.nan,
                                })
                                next_id += 1
                        else:
                            # Caso contrário (1 item ou sem custos), usa o fluxo antigo com fallback de dados
                            all_new_rows.append({
                                "IDManutencao":       next_id,
                                "IDOrdServ":          os_obj.numero_os,
                                "TotalOS":            float(os_obj.total_os) if os_obj.total_os else np.nan,
                                "Empresa":            os_obj.empresa,
                                "Placa":              os_obj.placa,
                                "IDVeiculo":          os_obj.id_veiculo,
                                "Modelo":             os_obj.modelo,
                                "Implemento":         os_obj.implemento,
                                "Fornecedor":         nf.fornecedor or os_obj.fornecedor,
                                "Nota":               nf.numero_nf,
                                "Data Venc.":         pd.to_datetime(p.data_vencimento).strftime("%Y-%m-%d") if p.data_vencimento else np.nan,
                                "ParcelaAtual":       p.parcela_atual,
                                "ParcelaTotal":       p.parcela_total,
                                "ValorParcela":       float(p.valor_parcela) if p.valor_parcela else np.nan,
                                "FormaPgto":          p.forma_pgto,
                                "Categoria":          nf.tipo_nf or os_obj.categoria,
                                "Status":             p.status_pagamento,
                                "TipoManutencao":     os_obj.tipo_manutencao,
                                "Sistema":            first_item.sistema if first_item else np.nan,
                                "Serviço":            first_item.servico if first_item else np.nan,
                                "KM":                 float(os_obj.km) if os_obj.km else np.nan,
                                "DataExecução":       pd.to_datetime(os_obj.data_execucao or os_obj.data_entrada).strftime("%Y-%m-%d") if (os_obj.data_execucao or os_obj.data_entrada) else np.nan,
                                "PosiçãoPneu":        first_item.posicao_pneu if first_item else np.nan,
                                "QtdPneu":            first_item.qtd_pneu if first_item else np.nan,
                                "EspecificaçãoPneu":  first_item.espec_pneu if first_item else np.nan,
                                "MarcaPneu":          first_item.marca_pneu    if first_item else np.nan,
                                "ModeloPneu":         first_item.modelo_pneu   if first_item else np.nan,
                                "CondicaoPneu":       first_item.condicao_pneu if first_item else np.nan,
                                "ManejoPneu":         first_item.manejo_pneu   if first_item else np.nan,
                            })
                            next_id += 1
            else:
                # OS sem NFs: grava linha de resumo
                all_new_rows.append({
                    "IDManutencao":   next_id,
                    "IDOrdServ":      os_obj.numero_os,
                    "TotalOS":        float(os_obj.total_os) if os_obj.total_os else np.nan,
                    "Placa":          os_obj.placa,
                    "IDVeiculo":      os_obj.id_veiculo,
                    "Modelo":         os_obj.modelo,
                    "Implemento":     os_obj.implemento,
                    "Fornecedor":     os_obj.fornecedor,
                    "Categoria":      os_obj.categoria,
                    "TipoManutencao": os_obj.tipo_manutencao,
                    "Sistema":        first_item.sistema if first_item else np.nan,
                    "Serviço":        first_item.servico if first_item else np.nan,
                    "KM":             float(os_obj.km) if os_obj.km else np.nan,
                    "DataExecução":   pd.to_datetime(os_obj.data_execucao or os_obj.data_entrada).strftime("%Y-%m-%d") if (os_obj.data_execucao or os_obj.data_entrada) else np.nan,
                    "PosiçãoPneu":    first_item.posicao_pneu if first_item else np.nan,
                    "QtdPneu":        first_item.qtd_pneu if first_item else np.nan,
                    "EspecificaçãoPneu": first_item.espec_pneu if first_item else np.nan,
                    "MarcaPneu":      first_item.marca_pneu    if first_item else np.nan,
                    "ModeloPneu":     first_item.modelo_pneu   if first_item else np.nan,
                    "CondicaoPneu":   first_item.condicao_pneu if first_item else np.nan,
                    "ManejoPneu":     first_item.manejo_pneu   if first_item else np.nan,
                })
                next_id += 1

        if not all_new_rows:
            return 0

        df_new = pd.DataFrame(all_new_rows)
        # Normaliza case de colunas para corresponder às existentes
        col_map = {c.lower(): c for c in df.columns}
        df_new.rename(columns={c: col_map.get(c.lower(), c) for c in df_new.columns}, inplace=True)
        for col in df.columns:
            if col not in df_new.columns:
                df_new[col] = np.nan
        df_new = df_new.reindex(columns=df.columns)

        df_final = pd.concat([df, df_new], ignore_index=True)
        try:
            with pd.ExcelWriter(EXCEL_PATH, mode="a", engine="openpyxl", if_sheet_exists="replace") as writer:
                df_final.to_excel(writer, sheet_name=sheet_name, index=False)
            _cache.clear()
            logger.info("sync_db_to_excel: %d linhas adicionadas ao Excel", len(all_new_rows))
        except PermissionError:
            logger.warning("sync_db_to_excel: Excel aberto — não foi possível salvar")
            return 0
        except Exception as e:
            logger.error("sync_db_to_excel escrita: %s", e)
            return 0

        return len(all_new_rows)
    except Exception as e:
        logger.error("sync_db_to_excel error: %s", e)
        return 0
    finally:
        db.close()


def _sync_manutencoes_background():
    """Executa sincronização bidirecional em background no startup."""
    try:
        n1 = sync_excel_to_db()
        n2 = sync_db_to_excel()
        if n1 or n2:
            logger.info("Sync concluído: %d Excel→DB | %d DB→Excel", n1, n2)
    except Exception as e:
        logger.error("_sync_manutencoes_background error: %s", e)


@app.on_event("startup")
def startup():
    init_db()
    _migrate_parcelas_prorrogacao()
    _migrate_1to1_safe()
    threading.Thread(target=_sync_manutencoes_background, daemon=True).start()
    threading.Thread(target=_enrich_km_from_mapws, daemon=True).start()


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

    Seguro em concorrência (SQLite serializa writes). Sincroniza com o maior
    número de OS já existente no banco para evitar conflitos após migrações.
    """
    from sqlalchemy import text
    from datetime import datetime as _dt
    year = _dt.now().year
    
    # 1. Descobre o maior número de OS já existente (nova ou legado)
    row_max = db.execute(text("""
        SELECT COALESCE(MAX(CAST(SUBSTR(numero_os, 9) AS INTEGER)), 0) FROM (
            SELECT numero_os FROM ordens_servico WHERE numero_os LIKE 'OS-' || :y || '-%'
            UNION ALL
            SELECT id_ord_serv as numero_os FROM manutencoes WHERE id_ord_serv LIKE 'OS-' || :y || '-%'
        )
    """), {"y": year}).fetchone()
    max_existente = row_max[0] if row_max else 0

    # 2. Garante que o contador nunca seja menor que o máximo existente
    db.execute(text("""
        INSERT INTO os_counters (ano, ultimo) VALUES (:y, :max_val)
        ON CONFLICT(ano) DO UPDATE SET ultimo = MAX(ultimo, :max_val)
    """), {"y": year, "max_val": max_existente})

    # 3. Incrementa atomicamente e retorna o novo valor
    row = db.execute(text("""
        UPDATE os_counters SET ultimo = ultimo + 1 WHERE ano = :y
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
    """Converte código numérico de empresa (ex: '1.0') para RazaoSocial.
    SQL-first; fallback Excel logado."""
    if empresa_code is None:
        return None
    try:
        eid = int(float(empresa_code))
    except (ValueError, TypeError):
        return str(empresa_code)
    try:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            row = conn.execute(_text("SELECT nome FROM empresas WHERE id = :e"), {"e": eid}).fetchone()
            if row and row[0]:
                return str(row[0])
        logger.warning("[FC_FALLBACK] empresa_nome do Excel — codigo=%s", empresa_code)
    except Exception as _e:
        logger.warning("[FC_FALLBACK] empresa_nome SQL erro=%s", _e)
    df = data.get("empresas", pd.DataFrame())
    if df.empty or "IDEmpresa" not in df.columns:
        return str(empresa_code)
    row_xl = df[df["IDEmpresa"] == eid]
    if row_xl.empty:
        return str(empresa_code)
    nome = row_xl.iloc[0].get("RazaoSocial")
    return str(nome) if pd.notna(nome) else str(empresa_code)


def _contrato_ativo(data: dict, id_veiculo, data_exec) -> dict | None:
    """Retorna o contrato ativo para um veículo em uma data de execução.
    SQL-first; fallback Excel logado."""
    if not id_veiculo or not data_exec:
        return None
    try:
        id_veiculo = int(id_veiculo)
        dc = pd.Timestamp(data_exec)
        dc_str = str(dc)[:10]
    except Exception:
        return None
    try:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            row = conn.execute(_text("""
                SELECT c.nome_cliente, c.cidade_operacao, c.data_inicio,
                       c.data_fim, c.data_encerramento, c.status_contrato
                FROM contrato_veiculo cv
                JOIN contratos c ON c.id = cv.contrato_id
                WHERE cv.id_veiculo = :idv
                  AND (c.data_inicio IS NULL OR c.data_inicio <= :dt)
                  AND (c.data_encerramento IS NULL OR c.data_encerramento >= :dt)
                ORDER BY c.data_inicio DESC
                LIMIT 1
            """), {"idv": id_veiculo, "dt": dc_str}).fetchone()
            if row:
                return {
                    "contrato_nome":   str(row[0] or ""),
                    "contrato_cidade": str(row[1] or ""),
                    "contrato_inicio": str(row[2])[:10] if row[2] else None,
                    "contrato_fim":    str(row[3])[:10] if row[3] else None,
                    "contrato_status": str(row[5] or ""),
                }
        logger.warning("[FC_FALLBACK] contrato_ativo do Excel — id_veiculo=%s", id_veiculo)
    except Exception as _e:
        logger.warning("[FC_FALLBACK] contrato_ativo SQL erro=%s", _e)
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


def _col_like(df: pd.DataFrame, *fragments) -> str | None:
    """Retorna a primeira coluna cujo nome (lower) contém todos os fragmentos."""
    for c in df.columns:
        cl = c.lower()
        if all(f.lower() in cl for f in fragments):
            return c
    return None


def _dedup_manut(manut_raw: pd.DataFrame) -> pd.DataFrame:
    if not manut_raw.empty and "IDOrdServ" in manut_raw.columns:
        com_os = manut_raw.dropna(subset=["IDOrdServ"]).drop_duplicates(subset=["IDOrdServ"])
        sem_os = manut_raw[manut_raw["IDOrdServ"].isna()]
        return pd.concat([com_os, sem_os], ignore_index=True)
    return manut_raw.copy()


def _load_db_financials(year: int) -> dict:
    """Lê fat_unitario, seguro_mensal, impostos e rastreamento direto do banco.
    Retorna DataFrames com os mesmos nomes de coluna que o Excel (IDVeiculo, Medicao…).
    O banco é mais completo e atualizado que o Excel para essas tabelas."""
    result = {}
    try:
        with engine.connect() as conn:
            result["fat"] = pd.read_sql(
                "SELECT id_veiculo AS IDVeiculo, mes AS Mes, contrato AS Contrato, "
                "medicao AS Medicao, trabalhado AS Trabalhado, parado AS Parado "
                "FROM fat_unitario WHERE strftime('%Y', mes) = :y",
                conn, params={"y": str(year)},
            )
            result["fat"]["Mes"] = pd.to_datetime(result["fat"]["Mes"])

            result["seg"] = pd.read_sql(
                "SELECT id_veiculo AS IDVeiculo, vencimento AS Vencimento, valor AS Valor "
                "FROM seguro_mensal WHERE strftime('%Y', vencimento) = :y",
                conn, params={"y": str(year)},
            )
            result["seg"]["Vencimento"] = pd.to_datetime(result["seg"]["Vencimento"])

            result["imp"] = pd.read_sql(
                "SELECT id_veiculo AS IDVeiculo, ano_imposto AS AnoImposto, "
                "valor_total_final AS ValorTotalFinal FROM impostos WHERE ano_imposto = :y",
                conn, params={"y": year},
            )

            result["rast"] = pd.read_sql(
                "SELECT id_veiculo AS IDVeiculo, vencimento AS Vencimento, valor AS Valor "
                "FROM rastreamento WHERE strftime('%Y', vencimento) = :y",
                conn, params={"y": str(year)},
            )
            result["rast"]["Vencimento"] = pd.to_datetime(result["rast"]["Vencimento"])

            result["reimb"] = pd.read_sql(
                "SELECT id_veiculo AS IDVeiculo, emissao AS Emissão, "
                "valor_reembolso AS ValorReembolso "
                "FROM reembolsos WHERE strftime('%Y', emissao) = :y",
                conn, params={"y": str(year)},
            )
            if not result["reimb"].empty:
                result["reimb"]["Emissão"] = pd.to_datetime(result["reimb"]["Emissão"])

            result["fat_sh"] = pd.read_sql(
                "SELECT emissao AS Emissão, valor_locacoes AS ValorLocacoes, "
                "valor_recebido AS ValorRecebido "
                "FROM faturamento_mensal WHERE strftime('%Y', emissao) = :y",
                conn, params={"y": str(year)},
            )
            if not result["fat_sh"].empty:
                result["fat_sh"]["Emissão"] = pd.to_datetime(result["fat_sh"]["Emissão"])
    except Exception as e:
        logger.error("Erro ao carregar financeiros do banco: %s", e)
    return result


def compute(year: int):
    data = load_raw()

    frota  = data["frota"].copy()

    # Financeiros lidos do banco (autoritativo) em vez do Excel
    _db = _load_db_financials(year)
    fat    = _db.get("fat",  pd.DataFrame())
    seg    = _db.get("seg",  pd.DataFrame())
    imp    = _db.get("imp",  pd.DataFrame())
    rast   = _db.get("rast", pd.DataFrame())

    # Fallback para Excel se banco vazio (compatibilidade)
    if fat.empty:
        fat  = _filter_year(_parse(data["fat_unitario"].copy(),  "Mes"),         "Mes",       year)
    if seg.empty:
        seg  = _filter_year(_parse(data["seguro_mensal"].copy(), "Vencimento"),  "Vencimento", year)
    if imp.empty:
        imp  = data["impostos"].copy()
        if not imp.empty and "AnoImposto" in imp.columns:
            imp = imp[imp["AnoImposto"] == year].copy()
    if rast.empty:
        rast = _filter_year(_parse(data["rastreamento"].copy(),  "Vencimento"),  "Vencimento", year)

    reimb  = _db.get("reimb",  pd.DataFrame())
    fat_sh = _db.get("fat_sh", pd.DataFrame())
    if reimb.empty:
        logger.warning("[FC_FALLBACK] reembolsos do Excel — year=%s", year)
        reimb = _filter_year(_parse(data["reembolsos"].copy(), "Emissão"), "Emissão", year)
    if fat_sh.empty:
        logger.warning("[FC_FALLBACK] faturamento do Excel — year=%s", year)
        fat_sh = _filter_year(_parse(data["faturamento"].copy(), "Emissão"), "Emissão", year)

    logger.info(
        "[FC_FALLBACK] manut_raw lido do Excel em compute() year=%s — "
        "ordens_servico SQL é sobreposto em seguida; Excel serve como base histórica.", year,
    )
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
                cols_to_merge = [c for c in ["AnoModelo", "TabelaFipe", "ValorImplemento", "ValorTotal"] if c in frota.columns]
                if "Placa" in frota.columns and cols_to_merge:
                    excel_data = frota[["Placa"] + cols_to_merge].dropna(subset=["Placa"]).drop_duplicates(subset=["Placa"])
                    sql_frota = sql_frota.merge(excel_data, on="Placa", how="left")
                frota = pd.concat([frota, sql_frota], ignore_index=True).drop_duplicates(subset=["Placa"], keep="last")
            
            # 2. Carregar OS Finalizadas do SQL para o ano selecionado
            # TotalOS: para OS com parcelas usa a soma das parcelas com vencimento no ano;
            # para OS sem parcelas (legado/Excel) usa total_os ou soma das NFs.
            sql_os = pd.read_sql("""
                SELECT os.id as id_sql, os.id_veiculo as IDVeiculo, os.placa as Placa,
                       COALESCE(os.data_execucao, os.data_entrada) as DataExecução,
                       CASE
                         WHEN EXISTS (
                           SELECT 1 FROM notas_fiscais nf
                           JOIN manutencao_parcelas p ON p.nf_id = nf.id
                           WHERE nf.os_id = os.id AND nf.deletado_em IS NULL AND p.deletado_em IS NULL
                         )
                         THEN COALESCE(
                           (SELECT SUM(COALESCE(p.valor_atualizado, p.valor_parcela))
                            FROM manutencao_parcelas p
                            JOIN notas_fiscais nf ON nf.id = p.nf_id
                            WHERE nf.os_id = os.id
                              AND p.deletado_em IS NULL
                              AND nf.deletado_em IS NULL
                              AND strftime('%Y', p.data_vencimento) = :year),
                           0
                         )
                         ELSE COALESCE(os.total_os, (SELECT SUM(valor_total_nf) FROM notas_fiscais WHERE os_id = os.id AND deletado_em IS NULL), 0)
                       END as TotalOS,
                       os.fornecedor as Fornecedor, os.modelo as Modelo, os.numero_os as IDOrdServ,
                       os.tipo_manutencao as TipoManutencao, os.km as KM, os.prox_km as ProxKM, os.prox_data as ProxData,
                       (SELECT sistema FROM os_itens WHERE os_id = os.id LIMIT 1) as Sistema,
                       (SELECT servico FROM os_itens WHERE os_id = os.id LIMIT 1) as Serviço,
                       (SELECT COUNT(*) FROM notas_fiscais WHERE os_id = os.id AND deletado_em IS NULL) as qtd_notas
                FROM ordens_servico os
                WHERE os.deletado_em IS NULL
                  AND (
                    EXISTS (
                      SELECT 1 FROM notas_fiscais nf
                      JOIN manutencao_parcelas p ON p.nf_id = nf.id
                      WHERE nf.os_id = os.id AND nf.deletado_em IS NULL AND p.deletado_em IS NULL
                        AND strftime('%Y', p.data_vencimento) = :year
                    )
                    OR strftime('%Y', COALESCE(os.data_execucao, os.data_entrada)) = :year
                  )
            """, conn, params={"year": str(year)})
            
            if not sql_os.empty:
                # ── EXPLOSÃO DE SISTEMAS PARA O DASHBOARD ──────────────────────
                # Garante que custos de ordens com múltiplos sistemas sejam fracionados corretamente
                os_ids_list = [int(x) for x in sql_os["id_sql"].dropna().tolist()]
                if os_ids_list:
                    try:
                        placeholders = ','.join(['?'] * len(os_ids_list))
                        items_sql = f"""
                            SELECT i.os_id, COALESCE(i.sistema, 'Outros') as Sistema, 
                                   MAX(COALESCE(i.servico, '')) as Serviço,
                                   SUM(COALESCE(nfi.valor_total_item, 0)) as sys_cost
                            FROM os_itens i
                            LEFT JOIN nf_itens nfi ON nfi.os_item_id = i.id
                            WHERE i.os_id IN ({placeholders})
                            GROUP BY i.os_id, i.sistema
                        """
                        df_items = pd.read_sql(items_sql, conn, params=os_ids_list)
                        
                        if not df_items.empty:
                            exploded_rows = []
                            for _, os_row in sql_os.iterrows():
                                oid = int(os_row["id_sql"])
                                sub_items = df_items[df_items["os_id"] == oid]
                                
                                if sub_items.empty:
                                    exploded_rows.append(os_row)
                                    continue
                                
                                total_item_sum = float(sub_items["sys_cost"].sum())
                                orig_total = float(os_row["TotalOS"] or 0)
                                
                                if total_item_sum > 0:
                                    for _, it_row in sub_items.iterrows():
                                        nr = os_row.copy()
                                        nr["Sistema"] = it_row["Sistema"]
                                        nr["Serviço"] = it_row["Serviço"]
                                        nr["TotalOS"] = round(orig_total * (float(it_row["sys_cost"]) / total_item_sum), 2)
                                        exploded_rows.append(nr)
                                else:
                                    # Distribui igualmente se custos nos itens não informados
                                    share = 1.0 / len(sub_items)
                                    for _, it_row in sub_items.iterrows():
                                        nr = os_row.copy()
                                        nr["Sistema"] = it_row["Sistema"]
                                        nr["Serviço"] = it_row["Serviço"]
                                        nr["TotalOS"] = round(orig_total * share, 2)
                                        exploded_rows.append(nr)
                            
                            sql_os = pd.DataFrame(exploded_rows)
                    except Exception as ex_exp:
                        logger.error("Erro ao explodir sistemas na análise compute(): %s", ex_exp)

                sql_os["DataExecução"] = pd.to_datetime(sql_os["DataExecução"])
                
                # SQL prevalece sobre Excel: remove do Excel as OS que existem no SQL
                if not manut_raw.empty and "IDOrdServ" in manut_raw.columns:
                    sql_ids = set(sql_os["IDOrdServ"].dropna().unique())
                    manut_raw = manut_raw[~manut_raw["IDOrdServ"].isin(sql_ids)]

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

    base_cols = ["IDVeiculo", "Placa", "Marca", "Modelo", "Status", "Tipagem", "Implemento", "AnoModelo", "TabelaFipe", "ValorImplemento", "ValorTotal"]
    base_cols = [c for c in base_cols if c in frota.columns]

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
        .reset_index()
    )

    numeric_cols = [
        "ReceitaLocacao", "ReceitaReembolso", "ReceitaTotal", "CustoManutencao", 
        "CustoSeguro", "CustoImpostos", "CustoRastreamento", "CustoTotal", 
        "Trabalhado", "Parado"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

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
    # Also include years from OS records and faturamento_mensal in the DB
    try:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            rows = conn.execute(_text("""
                SELECT DISTINCT CAST(strftime('%Y', data_entrada) AS INTEGER) as yr
                FROM ordens_servico WHERE data_entrada IS NOT NULL
                UNION
                SELECT DISTINCT CAST(strftime('%Y', data_execucao) AS INTEGER) as yr
                FROM ordens_servico WHERE data_execucao IS NOT NULL
                UNION
                SELECT DISTINCT CAST(strftime('%Y', emissao) AS INTEGER) as yr
                FROM faturamento_mensal WHERE emissao IS NOT NULL
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


def _clean_year(val):
    if pd.isna(val) or val is None:
        return ""
    try:
        f = float(val)
        if f == 0.0:
            return ""
        return str(int(f))
    except Exception:
        pass
    s = str(val).strip()
    if s.lower() in ("nan", "none", "nat", "0", "0.0", "—", ""):
        return ""
    return s

def _clean_implemento(val):
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none", "nat", "0", "0.0", "—", ""):
        return ""
    return s

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
            "implemento":         _clean_implemento(row.get("Implemento", "")),
            "ano_modelo":         _clean_year(row.get("AnoModelo", "")),
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
    try:
        from sqlalchemy import text as _text
        with engine.connect() as conn:
            rows = conn.execute(_text(
                "SELECT DISTINCT contrato FROM fat_unitario "
                "WHERE contrato IS NOT NULL AND strftime('%Y', mes) = :y"
            ), {"y": str(year)}).fetchall()
            if rows:
                return {"regions": sorted(r[0] for r in rows if r[0])}
        logger.warning("[FC_FALLBACK] regions do Excel — year=%s", year)
    except Exception as _e:
        logger.warning("[FC_FALLBACK] regions SQL erro=%s", _e)
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
        "implemento": _clean_implemento(row.get("Implemento", "")),
        "status":     _s(row["Status"]),
        "contrato":   _s(row.get("Contrato", "—")),
        "valor_total": safe(row.get("ValorTotal", 0)),
        "valor_tabela": safe(row.get("TabelaFipe", 0)),
        "valor_implemento": safe(row.get("ValorImplemento", 0)),
        "ano_modelo": _clean_year(row.get("AnoModelo", "")),
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


@app.get("/api/maintenance_analysis/implemento")
def get_implemento_analysis(year: int = Query(..., ge=2000, le=2100)):
    """
    Análise de manutenção por implemento veicular.
    Retorna por tipo de implemento:
      - Quantas OS, custo total, quais sistemas, intervalo de KM entre manutenções.
    """
    try:
        with engine.connect() as conn:
            rows = pd.read_sql("""
                SELECT
                    os.id              AS os_id,
                    os.placa           AS placa,
                    COALESCE(f.implemento, os.implemento, '') AS implemento,
                    os.km              AS km,
                    oi.sistema         AS sistema,
                    oi.categoria       AS categoria,
                    COALESCE(os.total_os,
                        (SELECT SUM(valor_total_nf) FROM notas_fiscais
                         WHERE os_id = os.id AND deletado_em IS NULL), 0
                    )                  AS total_os,
                    COALESCE(os.data_execucao, os.data_entrada) AS data_exec
                FROM ordens_servico os
                LEFT JOIN os_itens oi    ON oi.os_id = os.id
                LEFT JOIN frota f        ON f.placa  = os.placa
                WHERE os.deletado_em IS NULL
                  AND os.status_os = 'finalizada'
                  AND strftime('%Y', COALESCE(os.data_execucao, os.data_entrada)) = :year
            """, conn, params={"year": str(year)})
    except Exception as e:
        logger.error("Erro em /api/maintenance_analysis/implemento: %s", e)
        return []

    if rows.empty:
        return []

    rows["implemento"] = rows["implemento"].fillna("").str.strip()
    rows["sistema"]    = rows["sistema"].fillna("").str.strip()
    rows["km"]         = pd.to_numeric(rows["km"], errors="coerce")

    # Custo por OS (deduplica parcelas múltiplas de uma mesma OS)
    os_cost = rows.drop_duplicates(subset="os_id")[["os_id", "placa", "implemento", "km", "total_os"]]

    result = []
    for impl, grp_impl in rows.groupby("implemento"):
        if not impl:
            continue

        os_ids   = grp_impl["os_id"].unique()
        os_grp   = os_cost[os_cost["os_id"].isin(os_ids)]
        total    = float(os_grp["total_os"].sum())
        n_os     = int(len(os_ids))
        placas   = sorted(os_grp["placa"].dropna().unique().tolist())

        # Sistemas — agrupado por (sistema, categoria)
        por_sistema = []
        for (sis, cat), g2 in grp_impl.groupby(["sistema", "categoria"]):
            if not sis:
                continue
            os_sis = os_cost[os_cost["os_id"].isin(g2["os_id"].unique())]
            por_sistema.append({
                "sistema":   sis,
                "categoria": cat or "",
                "count":     int(g2["os_id"].nunique()),
                "custo":     float(os_sis["total_os"].sum()),
            })
        por_sistema.sort(key=lambda x: x["custo"], reverse=True)

        # Intervalos de KM por sistema — por placa, depois média geral
        intervalos = []
        for sis, g_sis in grp_impl.groupby("sistema"):
            if not sis:
                continue
            diffs_all = []
            por_placa_km = {}
            for pl, g_pl in g_sis.groupby("placa"):
                kms = sorted(g_pl.merge(os_cost[["os_id", "km"]], on="os_id", how="left")["km_y"]
                             .dropna().unique().tolist())
                if len(kms) >= 2:
                    d = [kms[i+1] - kms[i] for i in range(len(kms)-1) if kms[i+1] > kms[i]]
                    if d:
                        diffs_all.extend(d)
                        por_placa_km[pl] = round(sum(d) / len(d))
            if diffs_all:
                intervalos.append({
                    "sistema":        sis,
                    "intervalo_medio": round(sum(diffs_all) / len(diffs_all)),
                    "intervalo_min":   round(min(diffs_all)),
                    "intervalo_max":   round(max(diffs_all)),
                    "amostras":        len(diffs_all),
                    "por_placa":       por_placa_km,
                })
        intervalos.sort(key=lambda x: x["amostras"], reverse=True)

        result.append({
            "implemento":  impl,
            "total_os":    n_os,
            "total_custo": total,
            "placas":      placas,
            "n_placas":    len(placas),
            "por_sistema": por_sistema,
            "intervalos_km": intervalos,
        })

    result.sort(key=lambda x: x["total_custo"], reverse=True)
    return result


@app.get("/api/maintenance_analysis/intervalos")
def get_intervalos_analysis(sistema: str = Query(...)):
    """
    Análise de intervalos entre eventos de um mesmo sistema por veículo.
    Usa TODO o histórico (Excel + SQL, todos os anos) para intervalos reais.
    Para Pneu: agrupa por especificação e inclui KM atual do veículo via MAPWS.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from datetime import date, timedelta

    is_revisao = sistema.strip().lower() in ("revisão", "revisao")
    sis_lower  = sistema.strip().lower()
    is_pneu    = sis_lower == "pneu"

    # _col_like is now module-level

    # ── 1. Dados do Excel (histórico legado, todos os anos) ──────────
    rows_excel = pd.DataFrame()
    try:
        raw      = load_raw()
        frota_df = raw["frota"].copy()
        # Para pneu: NÃO usar _dedup_manut — precisamos de TODAS as linhas por OS
        # (cada linha = um item distinto, ex: DIANTEIRO e TRASEIRO separados)
        if is_pneu:
            manut_raw = _parse(raw["manutencoes"].copy(), "DataExecução")
        else:
            manut_raw = _dedup_manut(_parse(raw["manutencoes"].copy(), "DataExecução"))

        if not manut_raw.empty and "Sistema" in manut_raw.columns:
            col_serv  = _col_like(manut_raw, "servi") or "Serviço"
            col_data  = _col_like(manut_raw, "data", "exec") or "DataExecução"
            col_pos   = _col_like(manut_raw, "posi", "pneu")
            col_espec = _col_like(manut_raw, "especif", "pneu")

            if is_revisao:
                sc = manut_raw.get(col_serv, pd.Series("", index=manut_raw.index)).fillna("").str.lower()
                mask = (manut_raw["Sistema"].fillna("").str.lower().isin(["revisão", "motor"])) & \
                       (sc.str.contains("óleo|oleo|revis", na=False))
            else:
                mask = manut_raw["Sistema"].fillna("").str.lower() == sis_lower

            filtered = manut_raw[mask].copy()

            # Para pneu: apenas categoria Compra ou ManejoPneu = Recapadora
            if is_pneu and not filtered.empty:
                cat_col   = filtered.get("Categoria",  pd.Series("", index=filtered.index)).fillna("").str.lower()
                manejo_col_name = _col_like(filtered, "manejo", "pneu")
                manejo_col = filtered.get(manejo_col_name, pd.Series("", index=filtered.index)).fillna("").str.lower() \
                             if manejo_col_name else pd.Series("", index=filtered.index)
                keep = (cat_col == "compra") | (manejo_col == "recapadora")
                filtered = filtered[keep].copy()
                # Dedup por (IDOrdServ, posição): Excel tem 1 linha por parcela, queremos 1 por compra
                if not filtered.empty:
                    dedup_cols = ["IDOrdServ", col_pos] if col_pos and col_pos in filtered.columns else ["IDOrdServ"]
                    filtered = filtered.drop_duplicates(subset=dedup_cols)

            # Enriquecer com Implemento e Modelo da frota
            if not filtered.empty and "IDVeiculo" in filtered.columns and not frota_df.empty:
                frota_slim = frota_df[["IDVeiculo", "Placa", "Modelo", "Implemento"]].drop_duplicates("IDVeiculo") \
                    if all(c in frota_df.columns for c in ["IDVeiculo", "Placa", "Modelo", "Implemento"]) else None
                if frota_slim is not None:
                    filtered = filtered.merge(frota_slim, on="IDVeiculo", how="left", suffixes=("", "_frota"))
                    for c in ["Placa", "Modelo", "Implemento"]:
                        fc = c + "_frota"
                        if fc in filtered.columns:
                            filtered[c] = filtered[c].combine_first(filtered[fc])
                            filtered.drop(columns=[fc], inplace=True)

            needed = ["Placa", "Modelo", "Implemento", col_data, "KM", "IDOrdServ", "Sistema", "Categoria"]
            if col_serv and col_serv != "IDOrdServ" and col_serv not in needed:
                needed.append(col_serv)
            pneu_extra = [col_pos, "QtdPneu", col_espec, "MarcaPneu", "ModeloPneu", "CondicaoPneu", "ManejoPneu"]
            if is_pneu:
                needed += [c for c in pneu_extra if c and c not in needed]
            for c in needed:
                if c not in filtered.columns:
                    filtered[c] = None

            rename_map = {
                col_data:    "data_exec", "KM":        "km",
                "IDOrdServ": "numero_os", "Sistema":   "sistema_val",
                "Placa":     "placa",     "Modelo":    "modelo",
                "Implemento":"implemento","Categoria": "categoria",
            }
            if col_serv and col_serv != "IDOrdServ":
                rename_map[col_serv] = "servico"

            rows_excel = filtered[needed].rename(columns=rename_map)
            if is_pneu:
                rows_excel = rows_excel.rename(columns={
                    col_pos:          "posicao_pneu",
                    "QtdPneu":        "qtd_pneu",
                    col_espec:        "espec_pneu",
                    "MarcaPneu":      "marca_pneu",
                    "ModeloPneu":     "modelo_pneu",
                    "CondicaoPneu":   "condicao_pneu",
                    "ManejoPneu":     "manejo_pneu",
                })
            rows_excel["fonte"] = "excel"
            for col in ["servico", "categoria", "posicao_pneu", "qtd_pneu", "espec_pneu", "marca_pneu", "modelo_pneu", "condicao_pneu", "manejo_pneu", "descricao", "qtd_itens"]:
                if col not in rows_excel.columns:
                    rows_excel[col] = None
    except Exception as e:
        logger.error("Erro ao carregar Excel em /api/intervalos: %s", e)

    # ── 2. Dados do SQL (todos os anos, com os_itens expandidos) ────
    rows_sql = pd.DataFrame()
    try:
        if is_revisao:
            sis_sql_filter = "LOWER(oi.sistema) IN ('motor', 'revisão') AND (LOWER(oi.servico) LIKE '%óleo%' OR LOWER(oi.servico) LIKE '%oleo%' OR LOWER(oi.servico) LIKE '%revis%')"
        else:
            sis_sql_filter = f"LOWER(oi.sistema) = '{sis_lower.replace(chr(39), '')}'"

        pneu_filter = ""
        if is_pneu:
            pneu_filter = """
              AND (
                LOWER(COALESCE(oi.categoria,'')) = 'compra'
                OR LOWER(COALESCE(oi.manejo_pneu,'')) = 'recapadora'
              )
            """

        with engine.connect() as conn:
            rows_sql = pd.read_sql(f"""
                SELECT
                    os.placa                                    AS placa,
                    os.modelo                                   AS modelo,
                    COALESCE(f.implemento, os.implemento, '')   AS implemento,
                    COALESCE(os.data_execucao, os.data_entrada) AS data_exec,
                    os.km                                       AS km,
                    os.numero_os                                AS numero_os,
                    oi.sistema                                  AS sistema_val,
                    oi.servico                                  AS servico,
                    oi.descricao                                AS descricao,
                    oi.qtd_itens                                AS qtd_itens,
                    oi.posicao_pneu                             AS posicao_pneu,
                    oi.qtd_pneu                                 AS qtd_pneu,
                    oi.espec_pneu                               AS espec_pneu,
                    oi.marca_pneu                               AS marca_pneu,
                    oi.modelo_pneu                              AS modelo_pneu,
                    oi.condicao_pneu                            AS condicao_pneu,
                    oi.manejo_pneu                              AS manejo_pneu,
                    oi.categoria                                AS categoria,
                    os.fornecedor                               AS fornecedor
                FROM ordens_servico os
                JOIN os_itens oi  ON oi.os_id = os.id
                LEFT JOIN frota f ON f.placa   = os.placa
                WHERE os.deletado_em IS NULL
                  AND os.status_os   = 'finalizada'
                  AND {sis_sql_filter}
                  {pneu_filter}
            """, conn)
            rows_sql["fonte"] = "sql"
    except Exception as e:
        logger.error("Erro ao carregar SQL em /api/intervalos: %s", e)

    # ── 3. Combinar ──────────────────────────────────────────────────
    if rows_sql.empty and rows_excel.empty:
        return {"sistema": sistema, "fleet": {}, "por_placa": []}

    if is_pneu:
        # SQL autoritativo para QUALQUER row pneu — mesmo sem posicao_pneu preenchida.
        # Excel complementa posicao_pneu ausente no SQL e cobre OS totalmente ausentes do SQL.
        frames_pneu = []
        sql_nos = set(rows_sql["numero_os"].dropna().unique()) if not rows_sql.empty else set()

        if not rows_sql.empty:
            rows_sql_base = rows_sql.copy()
            # Backfill posicao_pneu de Excel para rows SQL que ainda não têm posição
            if not rows_excel.empty:
                pos_xl = (
                    rows_excel[rows_excel["posicao_pneu"].notna()]
                    [["numero_os", "posicao_pneu"]]
                    .drop_duplicates("numero_os")
                    .set_index("numero_os")["posicao_pneu"]
                )
                mask_no_pos = (
                    rows_sql_base["posicao_pneu"].isna()
                    | (rows_sql_base["posicao_pneu"].astype(str).str.strip() == "")
                )
                rows_sql_base.loc[mask_no_pos, "posicao_pneu"] = (
                    rows_sql_base.loc[mask_no_pos, "numero_os"].map(pos_xl)
                )
            frames_pneu.append(rows_sql_base)

        if not rows_excel.empty:
            # Excel apenas para OS completamente ausentes do SQL
            excel_only = rows_excel[~rows_excel["numero_os"].isin(sql_nos)].copy()
            if not excel_only.empty:
                frames_pneu.append(excel_only)

        combined = pd.concat(frames_pneu, ignore_index=True) if frames_pneu else pd.DataFrame()
    else:
        frames  = [f for f in [rows_excel, rows_sql] if not f.empty]
        combined = pd.concat(frames, ignore_index=True)
        if "numero_os" in combined.columns:
            sql_os = set(combined[combined["fonte"] == "sql"]["numero_os"].dropna().unique())
            combined = combined[(combined["fonte"] == "sql") | (~combined["numero_os"].isin(sql_os))]

    combined["km"]        = pd.to_numeric(combined["km"], errors="coerce")
    combined["data_exec"] = pd.to_datetime(combined["data_exec"], errors="coerce")

    # ── 3.1. Enriquecer data_exec, modelo e km ausentes a partir do SQL ──────
    # OS registradas apenas no novo sistema (SQL) mas sem posicao_pneu caem no
    # caminho Excel e ficam sem data/modelo/km. Busca ordens_servico para preencher.
    if not combined.empty:
        null_mask = (
            combined["data_exec"].isna()
            | combined["modelo"].fillna("").str.strip().eq("")
            | combined["km"].isna()
        )
        if null_mask.any():
            nos_list = combined.loc[null_mask, "numero_os"].dropna().unique().tolist()
            if nos_list:
                nos_str = ", ".join(f"'{n.replace(chr(39), '')}'" for n in nos_list)
                try:
                    with engine.connect() as _c:
                        enrich_df = pd.read_sql(
                            f"SELECT numero_os, COALESCE(data_execucao, data_entrada) AS data_exec_sql, "
                            f"modelo AS modelo_sql, km AS km_sql FROM ordens_servico "
                            f"WHERE deletado_em IS NULL AND numero_os IN ({nos_str})",
                            _c,
                        )
                    if not enrich_df.empty:
                        enrich_df["data_exec_sql"] = pd.to_datetime(enrich_df["data_exec_sql"], errors="coerce")
                        enrich_df["km_sql"] = pd.to_numeric(enrich_df["km_sql"], errors="coerce")
                        combined = combined.merge(enrich_df, on="numero_os", how="left")
                        m_date   = combined["data_exec"].isna() & combined["data_exec_sql"].notna()
                        combined.loc[m_date, "data_exec"] = combined.loc[m_date, "data_exec_sql"]
                        m_mod    = combined["modelo"].fillna("").str.strip().eq("") & combined["modelo_sql"].notna() & (combined["modelo_sql"].fillna("") != "")
                        combined.loc[m_mod, "modelo"] = combined.loc[m_mod, "modelo_sql"]
                        m_km     = combined["km"].isna() & combined["km_sql"].notna()
                        combined.loc[m_km, "km"] = combined.loc[m_km, "km_sql"]
                        combined.drop(columns=["data_exec_sql", "modelo_sql", "km_sql"], inplace=True)
                except Exception as _e:
                    logger.warning("Erro ao enriquecer data/modelo/km em intervalos: %s", _e)

    # ── 3.2. Enriquecer campos os_itens para rows Excel de pneu ───────────────────────
    # Rows Excel não carregam posicao_pneu, espec_pneu, servico, categoria, descricao etc.
    # Consulta os_itens para backfill desses campos quando disponíveis no SQL.
    if is_pneu and not combined.empty and "fonte" in combined.columns:
        xl_mask = combined["fonte"].eq("excel")
        xl_nos  = combined.loc[xl_mask, "numero_os"].dropna().unique().tolist()
        if xl_nos:
            nos_str2 = ", ".join(f"'{n.replace(chr(39), '')}'" for n in xl_nos)
            try:
                with engine.connect() as _c2:
                    enrich_items = pd.read_sql(f"""
                        SELECT os.numero_os,
                               oi.posicao_pneu  AS posicao_pneu_sql,
                               oi.espec_pneu    AS espec_pneu_sql,
                               oi.qtd_pneu      AS qtd_pneu_sql,
                               oi.marca_pneu    AS marca_pneu_sql,
                               oi.modelo_pneu   AS modelo_pneu_sql,
                               oi.condicao_pneu AS condicao_pneu_sql,
                               oi.servico       AS servico_sql,
                               oi.categoria     AS categoria_sql,
                               oi.descricao     AS descricao_sql,
                               oi.qtd_itens     AS qtd_itens_sql
                        FROM ordens_servico os
                        JOIN os_itens oi ON oi.os_id = os.id
                        WHERE os.deletado_em IS NULL
                          AND LOWER(oi.sistema) = 'pneu'
                          AND (LOWER(COALESCE(oi.categoria,'')) = 'compra'
                               OR LOWER(COALESCE(oi.manejo_pneu,'')) = 'recapadora')
                          AND os.numero_os IN ({nos_str2})
                    """, _c2)
                if not enrich_items.empty:
                    combined = combined.merge(enrich_items, on="numero_os", how="left")
                    for _field in ["posicao_pneu", "espec_pneu", "qtd_pneu", "marca_pneu",
                                   "modelo_pneu", "condicao_pneu", "servico", "categoria",
                                   "descricao", "qtd_itens"]:
                        _sql_col = f"{_field}_sql"
                        if _sql_col in combined.columns:
                            _m = combined[_field].isna() & combined[_sql_col].notna()
                            combined.loc[_m, _field] = combined.loc[_m, _sql_col]
                    combined.drop(
                        columns=[c for c in combined.columns if c.endswith("_sql")],
                        inplace=True,
                    )
            except Exception as _e2:
                logger.warning("Erro ao enriquecer os_itens pneu em intervalos: %s", _e2)

    # ── 3.5. Carregar rodízios (Pneu) — indexados por os_ref para montagem de fases ──
    rods_by_os: dict = {}
    if is_pneu and not combined.empty:
        try:
            placas_list = list(combined["placa"].dropna().unique())
            placas_str  = ", ".join(f"'{p}'" for p in placas_list)
            with engine.connect() as conn:
                rod_df = pd.read_sql(
                    "SELECT id, placa, data, km, posicao_anterior, posicao_nova, "
                    "espec_pneu, marca_pneu, qtd, os_ref FROM pneu_rodizios "
                    f"WHERE placa IN ({placas_str})",
                    conn,
                )
            if not rod_df.empty:
                rod_df["data"] = pd.to_datetime(rod_df["data"], errors="coerce")
                rod_df["km"]   = pd.to_numeric(rod_df["km"], errors="coerce")
                for _, r in rod_df.iterrows():
                    key = str(r.get("os_ref") or "").strip()
                    if not key:
                        continue
                    rods_by_os.setdefault(key, []).append({
                        "id":               int(r["id"]) if pd.notna(r.get("id")) else None,
                        "km":               float(r["km"]) if pd.notna(r.get("km")) else None,
                        "data":             r["data"] if pd.notna(r.get("data")) else None,
                        "posicao_anterior": str(r["posicao_anterior"]) if pd.notna(r.get("posicao_anterior")) else None,
                        "posicao_nova":     str(r["posicao_nova"]) if pd.notna(r.get("posicao_nova")) else None,
                    })
                for key in rods_by_os:
                    rods_by_os[key].sort(key=lambda x: x["km"] or 0)
        except Exception as e:
            logger.warning("Erro ao carregar rodízios em intervalos: %s", e)

    # ── 4. KM atual via MAPWS (Pneu only — parallel) ─────────────────
    def _mapws_latest_km(placa: str):
        """Retorna (km_fim, date_str) do registro mais recente nos últimos 30 dias."""
        today = date.today()
        start = today - timedelta(days=30)
        try:
            resp = _requests.get(
                f"{MAPWS_BASE}/api/details/{placa}",
                params={"start_date": str(start), "end_date": str(today)},
                timeout=5,
            )
            if resp.status_code != 200:
                return None, None
            data = resp.json()
            records = data if isinstance(data, list) else (data.get("data") or data.get("records") or [])
            # API retorna registros do mais recente para o mais antigo (índice 0 = hoje)
            for rec in records:
                val = rec.get("km_fim") or rec.get("km_acumulado") or rec.get("odometro")
                dt  = rec.get("data") or rec.get("date")
                if val is not None:
                    # Converter DD/MM/YYYY → YYYY-MM-DD para cálculos com pandas
                    if dt and "/" in str(dt):
                        parts = str(dt).split("/")
                        dt = f"{parts[2]}-{parts[1]}-{parts[0]}" if len(parts) == 3 else dt
                    return float(val), str(dt)[:10] if dt else None
        except Exception:
            pass
        return None, None

    km_atual_map: dict = {}
    if is_pneu:
        placas_unicas = [str(p).replace("-","").strip().upper() for p in combined["placa"].dropna().unique()]
        with ThreadPoolExecutor(max_workers=min(len(placas_unicas), 8)) as ex:
            futures = {ex.submit(_mapws_latest_km, p): p for p in placas_unicas}
            for fut in as_completed(futures, timeout=12):
                placa_k = futures[fut]
                try:
                    km_atual_map[placa_k] = fut.result()
                except Exception:
                    km_atual_map[placa_k] = (None, None)

    # ── 5. Calcular intervalos por placa (e por medida para Pneu) ────
    all_km_diffs  = []
    all_dia_diffs = []
    por_placa     = []

    def _sv(row, col):
        v = row.get(col)
        return None if (v is None or (isinstance(v, float) and pd.isna(v))) else v

    def _build_eventos(sub_grp, prev_eventos=None):
        """Constrói lista de eventos com delta_km/delta_dias, acumulando em prev_eventos."""
        evts = list(prev_eventos) if prev_eventos else []
        km_diffs, dia_diffs = [], []
        for _, row in sub_grp.iterrows():
            km_val      = float(row["km"])           if pd.notna(row["km"])        else None
            data_val    = str(row["data_exec"])[:10] if pd.notna(row["data_exec"]) else None
            tipo_evento = row.get("tipo_evento") or "compra"
            delta_km = delta_dias = None
            if evts:
                prev = evts[-1]
                if km_val is not None and prev["km"] is not None:
                    d = km_val - prev["km"]
                    if d > 0:
                        delta_km = round(d)
                        # Só conta nas estatísticas de frota se for compra de pneu
                        if tipo_evento == "compra":
                            km_diffs.append(delta_km)
                if data_val and prev["data"]:
                    try:
                        d2 = (pd.Timestamp(data_val) - pd.Timestamp(prev["data"])).days
                        if d2 > 0:
                            delta_dias = d2
                            if tipo_evento == "compra":
                                dia_diffs.append(delta_dias)
                    except Exception:
                        pass
            id_rod = row.get("id_rodizio")
            ev = {
                "numero_os":       _sv(row, "numero_os"),
                "data":            data_val,
                "km":              km_val,
                "delta_km":        delta_km,
                "delta_dias":      delta_dias,
                "categoria":       _sv(row, "categoria"),
                "servico":         _sv(row, "servico"),
                "descricao":       _sv(row, "descricao"),
                "qtd_itens":       int(row["qtd_itens"])  if pd.notna(row.get("qtd_itens")) else None,
                "posicao_pneu":    _sv(row, "posicao_pneu"),
                "posicao_anterior":_sv(row, "posicao_anterior"),
                "qtd_pneu":        int(row["qtd_pneu"])   if pd.notna(row.get("qtd_pneu"))  else None,
                "espec_pneu":      _sv(row, "espec_pneu"),
                "marca_pneu":      _sv(row, "marca_pneu"),
                "manejo_pneu":     _sv(row, "manejo_pneu"),
                "tipo_evento":     tipo_evento,
                "id_rodizio":      int(id_rod) if id_rod is not None and not (isinstance(id_rod, float) and pd.isna(id_rod)) else None,
            }
            evts.append(ev)
        return evts, km_diffs, dia_diffs

    for placa_val, grp in combined.groupby("placa"):
        grp = grp.sort_values(["km", "data_exec"], na_position="last").reset_index(drop=True)
        modelo_val     = next((str(v) for v in grp["modelo"].dropna()     if str(v).strip()), None)
        implemento_val = next((str(v) for v in grp["implemento"].dropna() if str(v).strip()), None)

        if is_pneu:
            grp["_espec"] = grp["espec_pneu"].fillna("—")
            por_medida:    list = []
            all_conjs_flat: list = []

            # KM atual — necessário para calcular km_rodado da fase em uso
            placa_norm = str(placa_val).replace("-", "").strip().upper()
            km_atual, km_atual_data = km_atual_map.get(placa_norm, (None, None))

            def _pos_parts(p: str) -> list:
                """Divide 'DIANTEIRO + TRASEIRO' em ['DIANTEIRO', 'TRASEIRO']."""
                return [x.strip() for x in (p or "").split("+") if x.strip()]

            for espec_val, espec_grp in grp.groupby("_espec", sort=False):
                espec_grp = espec_grp.sort_values(["km", "data_exec"], na_position="last").reset_index(drop=True)

                # ── CORREÇÃO BUG: Inferência de posicao_pneu por look-ahead / look-behind ─
                # Quando posicao_pneu = NULL (ex: OS cadastrada sem informar posição), o
                # algoritmo de tokenização ignora o conjunto (pos == "—"), impedindo a
                # detecção de substituição cruzada.  A heurística:
                #   1. Look-ahead: se a próxima compra desta especificação tem posição definida,
                #      herda essa posição (padrão: substituto é instalado no mesmo eixo).
                #   2. Look-behind: se não há próxima, herda da compra anterior mais recente.
                _valid_pos_m = (
                    espec_grp["posicao_pneu"].notna()
                    & (espec_grp["posicao_pneu"].astype(str).str.strip() != "")
                    & (~espec_grp["posicao_pneu"].astype(str).str.strip().isin(["—", "nan", "None", "none"]))
                )
                _km_num_col = pd.to_numeric(espec_grp["km"], errors="coerce").fillna(-1.0)
                for _idx in espec_grp.index:
                    _p = str(espec_grp.at[_idx, "posicao_pneu"] or "").strip()
                    if not _p or _p in ("—", "nan", "None", "none"):
                        _km_i = _km_num_col.at[_idx]
                        _ahead = espec_grp[_valid_pos_m & (_km_num_col > _km_i)]
                        if not _ahead.empty:
                            espec_grp.at[_idx, "posicao_pneu"] = _ahead.iloc[0]["posicao_pneu"]
                        else:
                            _behind = espec_grp[_valid_pos_m & (_km_num_col < _km_i)]
                            if not _behind.empty:
                                espec_grp.at[_idx, "posicao_pneu"] = _behind.iloc[-1]["posicao_pneu"]

                # ── CORREÇÃO BUG: Inferência de qtd_pneu ──────────────────────────────────
                # Quando qtd_pneu = NULL, herda o qtd da compra mais próxima na mesma posição
                # e mesma especificação para garantir que a tokenização gere o número correto
                # de tokens e marque todos os pneus substituídos (não apenas o primeiro).
                for _idx in espec_grp.index:
                    if pd.isna(espec_grp.at[_idx, "qtd_pneu"]) or espec_grp.at[_idx, "qtd_pneu"] is None:
                        _pos_i = str(espec_grp.at[_idx, "posicao_pneu"] or "").strip()
                        if _pos_i and _pos_i not in ("—", "nan", "None"):
                            _qtd_src = espec_grp[
                                espec_grp["qtd_pneu"].notna()
                                & (espec_grp["posicao_pneu"].astype(str).str.strip() == _pos_i)
                            ]
                            if not _qtd_src.empty:
                                espec_grp.at[_idx, "qtd_pneu"] = _qtd_src.iloc[0]["qtd_pneu"]

                conjs:     list = []
                km_diffs:  list = []
                dia_diffs: list = []
                prev_km_by_pos:   dict = {}  # posicao -> km anterior nessa posição
                prev_data_by_pos: dict = {}

                for _, row in espec_grp.iterrows():
                    os_ref      = _sv(row, "numero_os") or ""
                    km_compra   = float(row["km"])       if pd.notna(row.get("km"))        else None
                    data_compra = row["data_exec"]       if pd.notna(row.get("data_exec")) else None
                    pos_inicial = _sv(row, "posicao_pneu") or "—"
                    pos_parts   = _pos_parts(pos_inicial) or [pos_inicial]

                    # Posições compostas (ex: DIANTEIRO + TRASEIRO) geram conjuntos independentes
                    qtd_row     = int(row["qtd_pneu"]) if pd.notna(row.get("qtd_pneu")) else None
                    qtd_per_pos = (qtd_row // len(pos_parts)) if (qtd_row and len(pos_parts) > 1) else qtd_row

                    for pos_single in pos_parts:
                        delta_km = delta_dias = None
                        prev_km   = prev_km_by_pos.get(pos_single)
                        prev_data = prev_data_by_pos.get(pos_single)
                        if prev_km is not None and km_compra is not None:
                            d = km_compra - prev_km
                            if d > 0:
                                delta_km = round(d)
                                km_diffs.append(delta_km)
                        if prev_data is not None and data_compra is not None:
                            try:
                                d2 = (data_compra - prev_data).days
                                if d2 > 0:
                                    delta_dias = d2
                                    dia_diffs.append(delta_dias)
                            except Exception:
                                pass
                        prev_km_by_pos[pos_single]   = km_compra
                        prev_data_by_pos[pos_single] = data_compra

                        # Apenas rodízios cuja posicao_anterior bate com este sub-conjunto
                        rods  = [r for r in rods_by_os.get(os_ref, []) if r["posicao_anterior"] == pos_single]
                        fases = []
                        km_f   = km_compra or 0.0
                        data_f = data_compra
                        pos_f  = pos_single

                        for rod in rods:
                            km_r   = rod["km"] or 0.0
                            dias_f = None
                            if rod.get("data") is not None and data_f is not None:
                                try:
                                    dias_f = (pd.Timestamp(rod["data"]) - pd.Timestamp(str(data_f)[:10])).days
                                except Exception:
                                    pass
                            fases.append({
                                "posicao":     pos_f,
                                "km_inicio":   round(km_f),
                                "data_inicio": str(data_f)[:10] if data_f is not None else None,
                                "km_fim":      round(km_r),
                                "data_fim":    str(rod["data"])[:10] if rod.get("data") is not None else None,
                                "km_rodado":   max(0, round(km_r - km_f)),
                                "dias":        dias_f,
                                "em_uso":      False,
                                "id_rodizio":  rod.get("id"),
                            })
                            km_f   = km_r
                            data_f = rod["data"] if rod.get("data") is not None else data_f
                            pos_f  = rod["posicao_nova"] or pos_f

                        # Fase atual (pneu ainda em uso)
                        km_rodado_cur = round(float(km_atual or 0) - km_f) if km_atual else None
                        dias_cur = None
                        if km_atual_data and data_f is not None:
                            try:
                                dias_cur = (pd.Timestamp(km_atual_data) - pd.Timestamp(str(data_f)[:10])).days
                            except Exception:
                                pass
                        fases.append({
                            "posicao":     pos_f,
                            "km_inicio":   round(km_f),
                            "data_inicio": str(data_f)[:10] if data_f is not None else None,
                            "km_fim":      None,
                            "data_fim":    None,
                            "km_rodado":   max(0, km_rodado_cur) if km_rodado_cur is not None else None,
                            "dias":        dias_cur,
                            "em_uso":      True,
                            "id_rodizio":  None,
                        })

                        km_total = sum(f["km_rodado"] for f in fases if f["km_rodado"] is not None)
                        conjs.append({
                            "os_ref":          os_ref,
                            "compra_composta": len(pos_parts) > 1,  # veio de pos. composta, ex: DIANTEIRO+TRASEIRO
                            "data_compra":   str(data_compra)[:10] if data_compra is not None else None,
                            "km_compra":     round(km_compra) if km_compra is not None else None,
                            "marca":    _sv(row, "marca_pneu"),
                            "modelo":   _sv(row, "modelo_pneu"),
                            "condicao": _sv(row, "condicao_pneu"),
                            "recapado": "recap" in str(_sv(row, "manejo_pneu") or "").lower()
                                        or "recap" in str(_sv(row, "servico") or "").lower(),
                            "espec":    _sv(row, "espec_pneu"),
                            "qtd":           qtd_per_pos,
                            "delta_km":      delta_km,
                            "delta_dias":    delta_dias,
                            "km_total":      km_total,
                            "posicao_atual": pos_f,
                            "fases":         fases,
                        })

                all_km_diffs.extend(km_diffs)
                all_dia_diffs.extend(dia_diffs)
                all_conjs_flat.extend(conjs)
                total_pneus = sum(c["qtd"] or 0 for c in conjs)
                por_medida.append({
                    "espec":       espec_val,
                    "n_eventos":   len(conjs),
                    "total_pneus": total_pneus,
                    "avg_km":      round(sum(km_diffs) / len(km_diffs)) if km_diffs else None,
                    "min_km":      round(min(km_diffs)) if km_diffs else None,
                    "max_km":      round(max(km_diffs)) if km_diffs else None,
                    "conjuntos":   conjs,
                })

            # ── KM timeline do veículo (para interpolação quando OS sem km) ─────────
            _km_tl = sorted(
                ((str(row["data_exec"])[:10], float(row["km"]))
                 for _, row in grp.iterrows()
                 if pd.notna(row.get("km")) and float(row["km"]) > 0
                 and pd.notna(row.get("data_exec"))),
                key=lambda x: x[0],
            )

            def _km_at_date(dt_str):
                """Último km registrado em OS na data ou antes dela."""
                if not dt_str or not _km_tl:
                    return None
                best = None
                for d, km in _km_tl:
                    if d <= dt_str:
                        best = km
                    else:
                        break
                return best

            # ── Detectar descarte GLOBAL (cross-espec) ────────────────────────────
            # Qualquer novo pneu na mesma posição (independente de medida) descarta
            # o conjunto anterior. A lógica por-espec dentro do loop não captura isso.
            # ── Detectar descarte GLOBAL (cross-espec) com rastreamento por unidade ──────
            # Implementa fila de consumo dinâmico para suportar substituições parciais (ex: 1 novo repõe 1 de 2 antigos).
            import copy
            from collections import defaultdict
            
            # 1. Tokenização: Transforma conjuntos em tokens unitários independentes
            all_tokens = []
            for conj in all_conjs_flat:
                last_f = conj["fases"][-1]
                pos = last_f.get("posicao")
                if not pos or pos == "—": continue
                
                qtd = max(1, int(conj.get("qtd") or 1))
                for i in range(qtd):
                    for pp in (_pos_parts(pos) or [pos]):
                        all_tokens.append({
                            "conj_id": id(conj),
                            "conj": conj,
                            "pos": pp,
                            "km": last_f["km_inicio"] or 0,
                            "dt": last_f.get("data_inicio") or "",
                            "replaced_by": None
                        })
            
            # Ordena cronologicamente (km depois data)
            all_tokens.sort(key=lambda t: (t["km"], t["dt"] or ""))
            
            # 2. Algoritmo de Consumo Stateful: Cada token novo consome o token ativo mais antigo
            active_tokens_by_pos = {}
            for token in all_tokens:
                p = token["pos"]
                pool = active_tokens_by_pos.setdefault(p, [])
                
                # Candidatos a substituição: Devem ter chegado ANTES em km ou data, e vir de outro evento
                victims = [
                    v for v in pool 
                    if v["conj_id"] != token["conj_id"] 
                    and (token["km"] > v["km"] or (token["km"] == v["km"] and (token["dt"] or "") > (v["dt"] or "")))
                ]
                
                if victims:
                    victim = victims[0] # FIFO: consome o mais antigo da fila ativa
                    victim["replaced_by"] = token
                    pool.remove(victim)
                
                pool.append(token)

            # 3. Reconstrução Dinâmica: Divide conjuntos originais se houver destinos parciais mistos
            final_all_conjs = []
            
            # Mapeia tokens de volta para seu conjunto original para agrupar
            conj_to_tokens = defaultdict(list)
            for t in all_tokens:
                conj_to_tokens[id(t["conj"])].append(t)
                
            for orig_conj in all_conjs_flat:
                toks = conj_to_tokens.get(id(orig_conj))
                if not toks:
                    final_all_conjs.append(orig_conj)
                    continue
                
                # Agrupa tokens deste conjunto pelo destino do replacement (True/False e ID do causador)
                by_fate = defaultdict(list)
                for t in toks:
                    # Identificador do destino: None se ativo, ou ID do conj substituto se descartado
                    rid = id(t["replaced_by"]["conj"]) if t["replaced_by"] else None
                    by_fate[rid].append(t)
                
                # Gera conjuntos fracionados na saída
                for rid, sub_toks in by_fate.items():
                    c_split = copy.deepcopy(orig_conj)
                    c_split["qtd"] = len(sub_toks) # quantidade residual da fatia
                    l_f = c_split["fases"][-1]
                    
                    rep = sub_toks[0]["replaced_by"]
                    if rep:
                        r_f = rep["conj"]["fases"][-1]
                        nk = r_f["km_inicio"]
                        nd = r_f.get("data_inicio")
                        
                        l_f["km_fim"]   = nk if nk else None
                        l_f["data_fim"] = nd
                        km_entry = l_f["km_inicio"] or 0
                        
                        if (nk and km_entry) or (nk and not km_entry and nk > 0):
                            km_rod = max(0, round(nk - km_entry))
                        else:
                            d0 = l_f.get("data_inicio")
                            km_d0 = _km_at_date(d0) if d0 else None
                            km_d1 = _km_at_date(nd) if nd else None
                            km_rod = max(0, round(km_d1 - km_d0)) if (km_d0 is not None and km_d1 is not None) else None
                            
                        l_f["km_rodado"]  = km_rod
                        l_f["em_uso"]     = False
                        l_f["descartado"] = True
                        c_split["descartado"] = True
                    else:
                        # Sem substituto: Mantém ativo
                        l_f["em_uso"]     = True
                        l_f["descartado"] = False
                        c_split["descartado"] = False
                    
                    c_split["km_total"] = sum(f.get("km_rodado") or 0 for f in c_split["fases"])
                    final_all_conjs.append(c_split)

            # 4. Sincronização dos Resultados Finais
            all_conjs_flat = final_all_conjs # Atualiza lista plana global
            
            # Atualiza a árvore hierárquica retornada para o frontend
            for med in por_medida:
                m_espec = med["espec"]
                # Filtra da nova lista unificada apenas os que pertencem a esta medida específica
                med["conjuntos"] = [cj for cj in final_all_conjs if (cj.get("espec") or "—") == m_espec]
                med["n_eventos"] = len(med["conjuntos"])
                med["total_pneus"] = sum(cj.get("qtd") or 0 for cj in med["conjuntos"])


            # ── Recomputar ∆ KM / ∆ Dias globalmente por posição (cross-espec) ──
            # Ordena todos os conjuntos por km_compra e recalcula o delta contra o
            # conjunto ANTERIOR na mesma posição, independentemente da medida.
            pos_prev_km:   dict = {}
            pos_prev_data: dict = {}
            for conj in sorted(all_conjs_flat, key=lambda c: (c.get("km_compra") or 0)):
                pos = conj["fases"][0]["posicao"]
                prev_km   = pos_prev_km.get(pos)
                prev_data = pos_prev_data.get(pos)
                delta_km = delta_dias = None
                km_c   = conj.get("km_compra")
                data_c = conj.get("data_compra")
                if prev_km is not None and km_c is not None:
                    d = km_c - prev_km
                    if d > 0:
                        delta_km = round(d)
                if prev_data and data_c:
                    try:
                        d2 = (pd.Timestamp(data_c) - pd.Timestamp(prev_data)).days
                        if d2 > 0:
                            delta_dias = d2
                    except Exception:
                        pass
                conj["delta_km"]   = delta_km
                conj["delta_dias"] = delta_dias
                pos_prev_km[pos]   = km_c
                pos_prev_data[pos] = data_c

            por_medida.sort(key=lambda x: x["n_eventos"], reverse=True)

            # Per-posição: fase atual de cada conjunto, agrupado por posição
            # Posições compostas (ex: "DIANTEIRO + TRASEIRO") geram entradas em cada posição individual
            pos_map: dict = {}
            for conj in all_conjs_flat:
                if conj.get("descartado"):
                    continue
                last_f = conj["fases"][-1]
                for pp in _pos_parts(last_f["posicao"]) or [last_f["posicao"]]:
                    cur = pos_map.get(pp)
                    # Prioriza o conjunto instalado mais recentemente nessa posição
                    if cur is None or (conj.get("km_compra") or 0) > (cur["conj"].get("km_compra") or 0):
                        pos_map[pp] = {"conj": conj, "fase": last_f}

            km_por_posicao = [
                {
                    "posicao":      pos,
                    "km_troca":     item["fase"]["km_inicio"],
                    "data_troca":   item["fase"]["data_inicio"],
                    "marca":        item["conj"]["marca"],
                    "espec":        item["conj"]["espec"],
                    "qtd":          item["conj"]["qtd"],
                    "numero_os":    item["conj"]["os_ref"],
                    "km_rodado":    item["conj"]["km_total"],
                    "dias_rodando": sum(f["dias"] or 0 for f in item["conj"]["fases"]),
                }
                for pos, item in sorted(pos_map.items())
            ]

            kms_all = [c["km_compra"] for c in all_conjs_flat if c["km_compra"] is not None]
            por_placa.append({
                "placa":          placa_val,
                "modelo":         modelo_val,
                "implemento":     implemento_val,
                "n_eventos":      len(all_conjs_flat),
                "km_min":         round(min(kms_all)) if kms_all else None,
                "km_max":         round(max(kms_all)) if kms_all else None,
                "km_atual":       round(km_atual) if km_atual else None,
                "km_atual_data":  km_atual_data,
                "km_por_posicao": km_por_posicao,
                "por_medida":     por_medida,
            })
        else:
            evts, km_d, dia_d = _build_eventos(grp)
            all_km_diffs.extend(km_d)
            all_dia_diffs.extend(dia_d)
            kms = [e["km"] for e in evts if e["km"] is not None]
            por_placa.append({
                "placa":      placa_val,
                "modelo":     modelo_val,
                "implemento": implemento_val,
                "n_eventos":  len(evts),
                "km_min":     round(min(kms)) if kms else None,
                "km_max":     round(max(kms)) if kms else None,
                "eventos":    evts,
            })

    por_placa.sort(key=lambda x: x["n_eventos"], reverse=True)

    def _stats(lst):
        if not lst:
            return {"min": None, "avg": None, "max": None, "n": 0}
        return {"min": round(min(lst)), "avg": round(sum(lst)/len(lst)), "max": round(max(lst)), "n": len(lst)}

    return {
        "sistema": sistema,
        "fleet": {
            "km":             _stats(all_km_diffs),
            "dias":           _stats(all_dia_diffs),
            "total_eventos":  sum(p["n_eventos"] for p in por_placa),
            "total_veiculos": len(por_placa),
        },
        "por_placa": por_placa,
    }


# ═══════════════════════════════════════════════════════════════════
#  PNEU RODÍZIO — movimentações internas de posição
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/manut/pneu-rodizios/{placa}", response_model=list[schemas.PneuRodizioResponse])
def list_rodizios(placa: str, db: Session = Depends(get_db)):
    return db.query(models.PneuRodizio).filter(
        models.PneuRodizio.placa == placa.upper().replace("-", "")
    ).order_by(models.PneuRodizio.data).all()


@app.post("/api/manut/pneu-rodizios", response_model=schemas.PneuRodizioResponse, status_code=201)
def create_rodizio(payload: schemas.PneuRodizioCreate, db: Session = Depends(get_db)):
    obj = models.PneuRodizio(
        placa            = payload.placa.upper().replace("-", ""),
        data             = payload.data,
        km               = payload.km,
        posicao_anterior = payload.posicao_anterior,
        posicao_nova     = payload.posicao_nova,
        espec_pneu       = payload.espec_pneu,
        marca_pneu       = payload.marca_pneu,
        qtd              = payload.qtd,
        os_ref           = payload.os_ref,
        observacao       = payload.observacao,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/api/manut/pneu-rodizios/{rodizio_id}", status_code=204)
def delete_rodizio(rodizio_id: int, db: Session = Depends(get_db)):
    obj = db.query(models.PneuRodizio).get(rodizio_id)
    if not obj:
        raise HTTPException(404, "Rodízio não encontrado")
    db.delete(obj)
    db.commit()


# ═══════════════════════════════════════════════════════════════════
#  SINCRONIZAÇÃO Excel ↔ SQLite
# ═══════════════════════════════════════════════════════════════════

@app.post("/api/sync")
def run_sync():
    """Executa sincronização bidirecional Excel ↔ SQLite de forma síncrona.

    Retorna contagem de registros importados em cada direção.
    """
    try:
        n_excel_to_db = sync_excel_to_db()
        n_db_to_excel = sync_db_to_excel()
        return {
            "ok":           True,
            "excel_to_db":  n_excel_to_db,
            "db_to_excel":  n_db_to_excel,
        }
    except Exception as e:
        raise HTTPException(500, str(e))


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
            
            emp_val = nf.empresa_faturada or os_obj.empresa
            if str(emp_val).upper() == "TKJ": emp_val = "1"
            elif str(emp_val).upper() == "FINITA": emp_val = "2"
            elif str(emp_val).upper() == "LANDKRAFT": emp_val = "3"
            d["empresa"] = emp_val
            
            d["empresa_nome"]  = _empresa_nome(data, d["empresa"])
            d["id_contrato"]   = os_obj.id_contrato
            d["fornecedor_os"] = os_obj.fornecedor
            d["fornecedor"]    = getattr(p, "fornecedor", None) or nf.fornecedor or os_obj.fornecedor
            d["descricao"]     = "; ".join(filter(None, (it.servico or it.sistema for it in os_obj.itens))) or None
            d["sistema"]       = "; ".join(sorted(set(filter(None, (it.sistema for it in os_obj.itens))))) or None
            d["id_ord_serv"]   = os_obj.numero_os
            d["nota"]          = nf.numero_nf
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
            d["sistema"]       = manut.sistema
            d["id_ord_serv"]   = manut.id_ord_serv
            d["data_execucao"] = manut.data_execucao
            contrato = _contrato_ativo(data, manut.id_veiculo, manut.data_execucao)

        d["contrato_nome"]   = contrato["contrato_nome"]   if contrato else None
        d["contrato_cidade"] = contrato["contrato_cidade"] if contrato else None
        d["contrato_inicio"] = contrato["contrato_inicio"] if contrato else None
        d["contrato_fim"]    = contrato["contrato_fim"]    if contrato else None
        d["contrato_status"] = contrato["contrato_status"] if contrato else None

        # ── EXPLOSÃO POR SISTEMA ──────────────────────────────────────
        # Se possuir múltiplos itens, replicamos a parcela prorateada por custo de cada sistema
        if os_obj and getattr(nf, 'itens', None) and len(nf.itens) > 1:
            try:
                total_cost = sum(float(it.valor_total_item or 0) for it in nf.itens)
                if total_cost > 0:
                    # Agrupar por sistema para o caso de haver múltiplos itens do mesmo sistema
                    sys_weights = {}
                    sys_descs   = {}
                    for it in nf.itens:
                        sys_name = (it.os_item.sistema if it.os_item else None) or "Outros"
                        sys_weights[sys_name] = sys_weights.get(sys_name, 0.0) + float(it.valor_total_item or 0)
                        d_txt = (it.os_item.servico or it.os_item.descricao) if it.os_item else None
                        if d_txt:
                            if sys_name not in sys_descs: sys_descs[sys_name] = []
                            sys_descs[sys_name].append(d_txt)

                    for idx, (sys_name, sys_cost) in enumerate(sys_weights.items()):
                        ratio = sys_cost / total_cost
                        sd = d.copy()
                        sd["id"] = f"{p.id}_sis_{idx}" # chave id virtual única
                        sd["sistema"] = sys_name
                        
                        v_parc = float(p.valor_parcela or 0)
                        sd["valor_parcela"] = round(v_parc * ratio, 2)
                        if p.valor_atualizado is not None:
                            v_att = float(p.valor_atualizado)
                            sd["valor_atualizado"] = round(v_att * ratio, 2)
                        
                        if sys_name in sys_descs:
                            sd["descricao"] = "; ".join(filter(None, sorted(set(sys_descs[sys_name]))))
                        
                        result.append(sd)
                    continue # não adiciona o original agregado
            except Exception as e:
                logger.error("Erro na explosão de sistemas na parcela %s: %s", p.id, e)
        
        # Fallback padrão caso só tenha 1 item ou erro
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



@app.get("/api/db/pneu-specs/{placa}")
def get_pneu_specs(placa: str, db: Session = Depends(get_db)):
    """Retorna specs de pneu para uma placa: por posição (para auto-fill) e
    todas as medidas únicas conhecidas (para sugestões no datalist)."""
    from sqlalchemy import text as _text
    with engine.connect() as _c:
        # Rows COM posição — para auto-fill por posição
        rows_pos = _c.execute(_text("""
            SELECT oi.posicao_pneu, oi.espec_pneu, oi.marca_pneu, oi.modelo_pneu, oi.condicao_pneu,
                   COALESCE(os.data_execucao, os.data_entrada) AS ultima_data
            FROM os_itens oi
            JOIN ordens_servico os ON os.id = oi.os_id
            WHERE UPPER(os.placa) = UPPER(:placa)
              AND oi.posicao_pneu IS NOT NULL AND oi.posicao_pneu != ''
              AND oi.espec_pneu   IS NOT NULL AND oi.espec_pneu   != ''
              AND os.deletado_em  IS NULL
              AND LOWER(oi.sistema) = 'pneu'
              AND LOWER(COALESCE(oi.categoria,'')) = 'compra'
            ORDER BY ultima_data DESC
        """), {"placa": placa}).fetchall()

        # Todas as medidas distintas do veículo (independente de posição)
        rows_specs = _c.execute(_text("""
            SELECT DISTINCT oi.espec_pneu, oi.marca_pneu, oi.modelo_pneu, oi.condicao_pneu,
                   COALESCE(os.data_execucao, os.data_entrada) AS ultima_data
            FROM os_itens oi
            JOIN ordens_servico os ON os.id = oi.os_id
            WHERE UPPER(os.placa) = UPPER(:placa)
              AND oi.espec_pneu IS NOT NULL AND oi.espec_pneu != ''
              AND os.deletado_em IS NULL
              AND LOWER(oi.sistema) = 'pneu'
              AND LOWER(COALESCE(oi.categoria,'')) = 'compra'
            ORDER BY ultima_data DESC
        """), {"placa": placa}).fetchall()

    por_posicao: dict = {}
    for r in rows_pos:
        pos = (r[0] or "").strip().upper()
        if pos and pos not in por_posicao:
            por_posicao[pos] = {
                "espec_pneu":    r[1],
                "marca_pneu":    r[2],
                "modelo_pneu":   r[3],
                "condicao_pneu": r[4],
            }

    seen: set = set()
    specs_unicas: list = []
    for r in rows_specs:
        espec = r[0]
        if espec and espec not in seen:
            seen.add(espec)
            specs_unicas.append({
                "espec_pneu":    espec,
                "marca_pneu":    r[1],
                "modelo_pneu":   r[2],
                "condicao_pneu": r[3],
            })

    return {"por_posicao": por_posicao, "specs_unicas": specs_unicas}


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


@app.post("/api/db/enrich-km")
def trigger_enrich_km():
    """Dispara em background o preenchimento de KM nulo via MAPWS."""
    threading.Thread(target=_enrich_km_from_mapws, daemon=True).start()
    return {"status": "iniciado"}


@app.post("/api/db/os", response_model=schemas.OsResponse, status_code=201)
def abrir_os(payload: schemas.OsAbrir, db: Session = Depends(get_db)):
    veiculo = db.get(models.Frota, payload.id_veiculo)
    if not veiculo:
        raise HTTPException(404, f"Veículo {payload.id_veiculo} não encontrado")

    data = payload.model_dump(exclude={"itens"})
    
    # Auto-preenchimento de dados da frota
    if not data.get("modelo"):     data["modelo"]     = veiculo.modelo
    if not data.get("placa"):      data["placa"]      = veiculo.placa
    if not data.get("implemento"): data["implemento"] = veiculo.implemento
    if not data.get("empresa"):    data["empresa"]    = veiculo.empresa

    # Auto-preenchimento de categoria da OS pelo 1º item se vazio
    if not data.get("categoria") and payload.itens:
        first_cat = payload.itens[0].categoria
        if first_cat:
            data["categoria"] = first_cat

    # Resolução de fornecedor_id
    if data.get("fornecedor"):
        data["fornecedor_id"] = _resolve_fornecedor_id(db, data.get("fornecedor"))

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


def _sync_os_to_excel(os: models.OrdemServico):
    """Sincroniza OS finalizada para a aba 🔧 MANUTENCOES da planilha Locadora.xlsx."""
    import pandas as pd
    import numpy as np
    from pathlib import Path

    file_path = Path(__file__).parent.parent / "Locadora.xlsx"
    if not file_path.exists():
        logger.warning(f"Planilha {file_path} não encontrada para sincronização.")
        return

    try:
        with pd.ExcelFile(file_path) as xl:
            sheet_name = next((s for s in xl.sheet_names if "manutencao" in s.lower()), None)
            if not sheet_name:
                logger.warning("Aba de manutenção não encontrada no Excel.")
                return
            df = xl.parse(sheet_name)
    except PermissionError:
        raise HTTPException(
            status_code=400,
            detail="Erro ao ler a planilha Excel: o arquivo Locadora.xlsx está aberto. Por favor, feche-o e tente novamente."
        )
    except Exception as e:
        logger.error(f"Erro ao ler a planilha para sincronização: {e}")
        return

    # Se a OS já existe na aba de manutenções, removemos para evitar duplicidade
    if not df.empty and "IDOrdServ" in df.columns and os.numero_os:
        df = df[df["IDOrdServ"].astype(str).str.strip() != str(os.numero_os).strip()].copy()

    first_item = os.itens[0] if os.itens else None

    # Gerar novos IDs incrementais
    next_id = 1
    if not df.empty and "IDManutencao" in df.columns:
        valid_ids = pd.to_numeric(df["IDManutencao"], errors="coerce").dropna()
        if not valid_ids.empty:
            next_id = int(valid_ids.max()) + 1

    new_rows = []
    nfs_ativas = [nf for nf in os.notas_fiscais if nf.deletado_em is None]
    
    for nf in nfs_ativas:
        parcelas_ativas = [p for p in nf.parcelas if p.deletado_em is None]
        for p in parcelas_ativas:
            new_rows.append({
                "IDManutencao": next_id,
                "ValidaNovaOS": np.nan,
                "IDOrdServ": os.numero_os,
                "NFOrdem": nf.nf_ordem_origem if hasattr(nf, "nf_ordem_origem") and nf.nf_ordem_origem else np.nan,
                "TotalOS": float(os.total_os) if os.total_os else np.nan,
                "Empresa": os.empresa,
                "Placa": os.placa,
                "IDVeiculo": os.id_veiculo,
                "IDContrato": os.id_contrato,
                "Modelo": os.modelo,
                "Implemento": os.implemento,
                "Fornecedor": nf.fornecedor or os.fornecedor,
                "Nota": nf.numero_nf,
                "Data Venc.": pd.to_datetime(p.data_vencimento).strftime("%Y-%m-%d") if p.data_vencimento else np.nan,
                "ParcelaAtual": p.parcela_atual,
                "ParcelaTotal": p.parcela_total,
                "ValorParcela": float(p.valor_parcela) if p.valor_parcela else np.nan,
                "FormaPgto": p.forma_pgto,
                "Categoria": nf.tipo_nf or os.categoria,
                "Status": p.status_pagamento,
                "TipoManutencao": os.tipo_manutencao,
                "Sistema": first_item.sistema if first_item else np.nan,
                "Serviço": first_item.servico if first_item else np.nan,
                "Descricao": first_item.descricao if first_item else np.nan,
                "QtdItens": first_item.qtd_itens if first_item else np.nan,
                "KM": float(os.km) if os.km else np.nan,
                "PosiçãoPneu": first_item.posicao_pneu if first_item else np.nan,
                "QtdPneu": first_item.qtd_pneu if first_item else np.nan,
                "EspecificaçãoPneu": first_item.espec_pneu if first_item else np.nan,
                "MarcaPneu": first_item.marca_pneu if first_item else np.nan,
                "ManejoPneu": first_item.manejo_pneu if first_item else np.nan,
                "DataExecução": pd.to_datetime(os.data_execucao or os.data_entrada).strftime("%Y-%m-%d") if (os.data_execucao or os.data_entrada) else np.nan,
                "ResponsavelTec": os.responsavel_tec,
                "Indisponível": 1 if os.indisponivel else 0,
                "ProxKM": float(os.prox_km) if os.prox_km else np.nan,
                "ProxData": pd.to_datetime(os.prox_data).strftime("%Y-%m-%d") if os.prox_data else np.nan,
                "Obsercacoes": os.observacoes,
            })
            next_id += 1

    if new_rows:
        # Corrige case das colunas de acordo com as colunas já existentes no dataframe
        for r in new_rows:
            r_copy = r.copy()
            for k, v in r_copy.items():
                matching_col = next((c for c in df.columns if c.lower() == k.lower()), None)
                if matching_col and matching_col != k:
                    r[matching_col] = r.pop(k)

        df_new = pd.DataFrame(new_rows)
        # Garante que todas as colunas existem
        for col in df.columns:
            if col not in df_new.columns:
                df_new[col] = np.nan
        df_new = df_new[df.columns]
        
        df_final = pd.concat([df, df_new], ignore_index=True)
        
        try:
            with pd.ExcelWriter(file_path, mode="a", engine="openpyxl", if_sheet_exists="replace") as writer:
                df_final.to_excel(writer, sheet_name=sheet_name, index=False)
        except PermissionError:
            raise HTTPException(
                status_code=400,
                detail="Erro ao salvar na planilha Excel: o arquivo Locadora.xlsx está aberto. Por favor, feche-o e tente novamente."
            )
        except Exception as e:
            logger.error(f"Erro ao gravar os dados de OS na planilha: {e}")


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
    _sync_os_to_excel(os)
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


def _validar_nf_duplicada(db: Session, numero_nf: str, fornecedor: str, current_nf_id: int = None, os_id: int = None):
    if not numero_nf or not fornecedor:
        return
    n = str(numero_nf).strip()
    f = str(fornecedor).strip()
    if not n or not f:
        return
        
    q = db.query(models.NotaFiscal).filter(
        models.NotaFiscal.numero_nf == n,
        models.NotaFiscal.fornecedor == f,
        models.NotaFiscal.deletado_em == None
    )
    if os_id:
        q = q.filter(models.NotaFiscal.os_id == os_id)
        
    if current_nf_id:
        q = q.filter(models.NotaFiscal.id != current_nf_id)
        
    if q.first():
        raise HTTPException(400, f"A Nota Fiscal '{n}' já foi lançada para o fornecedor '{f}' nesta mesma OS.")

@app.post("/api/db/os/{os_id}/nfs", response_model=schemas.NotaFiscalResponse, status_code=201)
def adicionar_nf(os_id: int, payload: schemas.NotaFiscalCreate, db: Session = Depends(get_db)):
    os = db.get(models.OrdemServico, os_id)
    if not os or os.deletado_em is not None:
        raise HTTPException(404, "OS não encontrada")

    _validar_nf_duplicada(db, payload.numero_nf, payload.fornecedor, os_id=os_id)

    # Gera numero_os atomicamente na 1ª NF
    if os.numero_os is None:
        os.numero_os = generate_numero_os_atomic(db)

    # Propaga fornecedor para o cabeçalho da OS
    if payload.fornecedor:
        os.fornecedor = payload.fornecedor
        os.fornecedor_id = _resolve_fornecedor_id(db, payload.fornecedor)

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

    # Permite edição/recriação completa durante a finalização/edição da OS
    # para permitir que o usuário adicione notas fiscais e atualize parcelas.
    for old_nf in list(os_obj.notas_fiscais):
        db.delete(old_nf)
    db.flush()

    if os_obj.numero_os is None and payload:
        os_obj.numero_os = generate_numero_os_atomic(db)

    # Propaga o fornecedor da primeira Nota Fiscal recebida para o cabeçalho da OS
    if payload:
        first_f = payload[0].fornecedor
        if first_f:
            os_obj.fornecedor = first_f
            os_obj.fornecedor_id = _resolve_fornecedor_id(db, first_f)

    nfs_criadas = []
    for nf_data in payload:
        _validar_nf_duplicada(db, nf_data.numero_nf, nf_data.fornecedor, os_id=os_id)
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

    _validar_nf_duplicada(db, nf.numero_nf, nf.fornecedor, current_nf_id=nf.id, os_id=nf.os_id)

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
