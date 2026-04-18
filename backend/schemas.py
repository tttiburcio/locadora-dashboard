from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional


# ─────────────────────────────────────────────
# PARCELAS
# ─────────────────────────────────────────────
class ParcelaCreate(BaseModel):
    nf_ordem:        Optional[int]   = None
    nota:            Optional[str]   = None
    data_vencimento: Optional[date]  = None
    parcela_atual:   Optional[int]   = None
    parcela_total:   Optional[int]   = None
    valor_parcela:   Optional[float] = None
    forma_pgto:      Optional[str]   = None
    status_pagamento: str            = "Pendente"


class ParcelaUpdate(BaseModel):
    nota:                     Optional[str]   = None
    data_vencimento:          Optional[date]  = None
    valor_parcela:            Optional[float] = None
    forma_pgto:               Optional[str]   = None
    status_pagamento:         Optional[str]   = None
    data_vencimento_original: Optional[date]  = None
    prorrogada:               Optional[bool]  = None
    isento_encargos:          Optional[bool]  = None
    tipo_pgto_prorrogacao:    Optional[str]   = None
    chave_pix:                Optional[str]   = None
    multa_pct:                Optional[float] = None
    juros_diario_pct:         Optional[float] = None
    data_prevista_pagamento:  Optional[date]  = None
    dias_cartorio:            Optional[int]   = None
    valor_atualizado:         Optional[float] = None


class ParcelaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    manutencao_id:    int
    nf_ordem:         Optional[int]
    nota:             Optional[str]
    data_vencimento:  Optional[date]
    parcela_atual:    Optional[int]
    parcela_total:    Optional[int]
    valor_parcela:    Optional[float]
    forma_pgto:       Optional[str]
    status_pagamento: str
    data_vencimento_original: Optional[date]  = None
    prorrogada:               Optional[bool]  = None
    isento_encargos:          Optional[bool]  = None
    tipo_pgto_prorrogacao:    Optional[str]   = None
    chave_pix:                Optional[str]   = None
    multa_pct:                Optional[float] = None
    juros_diario_pct:         Optional[float] = None
    data_prevista_pagamento:  Optional[date]  = None
    dias_cartorio:            Optional[int]   = None
    valor_atualizado:         Optional[float] = None


class ParcelaFinanceiroResponse(ParcelaResponse):
    placa:         str
    modelo:        Optional[str]  = None
    fornecedor:    Optional[str]  = None
    id_ord_serv:   Optional[str]  = None
    data_execucao: Optional[date] = None


# ─────────────────────────────────────────────
# MANUTENÇÃO — criação (abertura)
# ─────────────────────────────────────────────
class ManutencaoAbrir(BaseModel):
    """Dados necessários ao abrir uma OS (veículo entrou em manutenção)."""
    id_veiculo:      int
    placa:           str
    modelo:          Optional[str]  = None
    empresa:         Optional[str]  = None
    id_contrato:     Optional[str]  = None
    implemento:      Optional[str]  = None
    fornecedor:      Optional[str]  = None
    tipo_manutencao: Optional[str]  = None   # Preventiva | Corretiva
    sistema:         Optional[str]  = None
    servico:         Optional[str]  = None
    descricao:       Optional[str]  = None
    km:              Optional[float] = None
    responsavel_tec: Optional[str]  = None
    indisponivel:    bool            = True
    data_entrada:    Optional[date]  = None
    status_manutencao: str           = "em_andamento"
    observacoes:     Optional[str]  = None


# ─────────────────────────────────────────────
# MANUTENÇÃO — atualização de status / dados gerais
# ─────────────────────────────────────────────
class ManutencaoUpdate(BaseModel):
    status_manutencao: Optional[str]   = None
    fornecedor:        Optional[str]   = None
    tipo_manutencao:   Optional[str]   = None
    sistema:           Optional[str]   = None
    servico:           Optional[str]   = None
    descricao:         Optional[str]   = None
    responsavel_tec:   Optional[str]   = None
    indisponivel:      Optional[bool]  = None
    data_entrada:      Optional[date]  = None
    km:                Optional[float] = None
    observacoes:       Optional[str]   = None


# ─────────────────────────────────────────────
# MANUTENÇÃO — finalização (preenchimento financeiro)
# ─────────────────────────────────────────────
class ManutencaoFinalizar(BaseModel):
    """Dados financeiros preenchidos ao concluir a OS."""
    id_ord_serv:     str
    total_os:        float
    data_execucao:   date
    km:              Optional[float] = None
    categoria:       Optional[str]   = None
    qtd_itens:       Optional[int]   = None
    prox_km:         Optional[float] = None
    prox_data:       Optional[date]  = None

    # ── Dados de pneu (opcional) ──────────────
    posicao_pneu: Optional[str] = None
    qtd_pneu:     Optional[int] = None
    espec_pneu:   Optional[str] = None
    marca_pneu:   Optional[str] = None
    manejo_pneu:  Optional[str] = None

    # ── Parcelas de pagamento ─────────────────
    parcelas: list[ParcelaCreate] = []


# ─────────────────────────────────────────────
# MANUTENÇÃO — response
# ─────────────────────────────────────────────
class ManutencaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                int
    status_manutencao: str
    id_veiculo:        int
    placa:             str
    modelo:            Optional[str]
    empresa:           Optional[str]
    id_contrato:       Optional[str]
    implemento:        Optional[str]
    fornecedor:        Optional[str]
    tipo_manutencao:   Optional[str]
    sistema:           Optional[str]
    servico:           Optional[str]
    descricao:         Optional[str]
    qtd_itens:         Optional[int]
    km:                Optional[float]
    posicao_pneu:      Optional[str]
    qtd_pneu:          Optional[int]
    espec_pneu:        Optional[str]
    marca_pneu:        Optional[str]
    manejo_pneu:       Optional[str]
    responsavel_tec:   Optional[str]
    indisponivel:      Optional[bool]
    data_entrada:      Optional[date]
    data_execucao:     Optional[date]
    id_ord_serv:       Optional[str]
    total_os:          Optional[float]
    categoria:         Optional[str]
    prox_km:           Optional[float]
    prox_data:         Optional[date]
    observacoes:       Optional[str]
    criado_em:         Optional[datetime]
    atualizado_em:     Optional[datetime]

    parcelas: list[ParcelaResponse] = []


# ─────────────────────────────────────────────
# FROTA — response simples (para selects)
# ─────────────────────────────────────────────
class FrotaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         int
    placa:      str
    modelo:     Optional[str]
    empresa:    Optional[str]
    status:     Optional[str]
    implemento: Optional[str]
