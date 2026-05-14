from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional, Literal, Union, Any


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
    fornecedor:               Optional[str]   = None
    valor_item_total:         Optional[float] = None
    tipo_custo:               Optional[str]   = None
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
    sera_reembolsado:         Optional[bool]  = None
    valor_reembolso:          Optional[float] = None
    qtd_itens_reembolso:      Optional[int]   = None
    motivo_reembolso:         Optional[str]   = None


class ParcelaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               Union[int, str]
    manutencao_id:    Optional[int] = None
    nf_id:            Optional[int] = None
    nf_ordem:         Optional[int]
    nota:             Optional[str]
    fornecedor:       Optional[str]   = None
    valor_item_total: Optional[float] = None
    tipo_custo:       Optional[str]   = None
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
    sera_reembolsado:         Optional[bool]  = None
    valor_reembolso:          Optional[float] = None
    qtd_itens_reembolso:      Optional[int]   = None
    motivo_reembolso:         Optional[str]   = None


class ParcelaFinanceiroResponse(ParcelaResponse):
    placa:            str
    modelo:           Optional[str]  = None
    empresa:          Optional[str]  = None
    empresa_nome:     Optional[str]  = None
    id_contrato:      Optional[str]  = None
    fornecedor_os:    Optional[str]  = None
    descricao:        Optional[str]  = None
    id_ord_serv:      Optional[str]  = None
    data_execucao:    Optional[date] = None
    contrato_nome:    Optional[str]  = None
    contrato_cidade:  Optional[str]  = None
    contrato_inicio:  Optional[str]  = None
    contrato_fim:     Optional[str]  = None
    contrato_status:  Optional[str]  = None
    sistema:          Optional[str]  = None


# ─────────────────────────────────────────────
# PNEU RODÍZIO
# ─────────────────────────────────────────────
class PneuRodizioCreate(BaseModel):
    placa:            str
    data:             date
    km:               Optional[int]   = None
    posicao_anterior: str
    posicao_nova:     str
    espec_pneu:       Optional[str]   = None
    marca_pneu:       Optional[str]   = None
    qtd:              Optional[int]   = 2
    os_ref:           Optional[str]   = None
    observacao:       Optional[str]   = None


class PneuRodizioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    placa:            str
    data:             date
    km:               Optional[int]   = None
    posicao_anterior: str
    posicao_nova:     str
    espec_pneu:       Optional[str]   = None
    marca_pneu:       Optional[str]   = None
    qtd:              Optional[int]   = None
    os_ref:           Optional[str]   = None
    observacao:       Optional[str]   = None
    criado_em:        Optional[datetime] = None


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
    empresa:           Optional[str]   = None
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
    empresa:         Optional[str]   = None
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


# ─────────────────────────────────────────────────────────────────────
# NOVO MODELO HIERÁRQUICO: OS → Itens → NFs → Itens da NF → Parcelas
# ─────────────────────────────────────────────────────────────────────

# ── OsItem ───────────────────────────────────────────────────────────
class OsItemBase(BaseModel):
    categoria:    Optional[str] = None
    sistema:      Optional[str] = None
    servico:      Optional[str] = None
    descricao:    Optional[str] = None
    qtd_itens:    Optional[int] = None
    posicao_pneu: Optional[str] = None
    qtd_pneu:     Optional[int] = None
    espec_pneu:   Optional[str] = None
    marca_pneu:   Optional[str] = None
    modelo_pneu:  Optional[str] = None
    condicao_pneu:Optional[str] = None
    manejo_pneu:  Optional[str] = None


class OsItemCreate(OsItemBase):
    pass


class OsItemUpdate(OsItemBase):
    pass


class OsItemEdit(OsItemBase):
    id: Optional[int] = None


class OsItemResponse(OsItemBase):
    model_config = ConfigDict(from_attributes=True)
    id:    int
    os_id: int


# ── NfItem ───────────────────────────────────────────────────────────
class NfItemBase(BaseModel):
    os_item_id:         int
    quantidade:         Optional[float] = 1
    valor_unitario:     Optional[float] = None
    valor_total_item:   Optional[float] = None
    descricao_override: Optional[str]   = None


class NfItemCreate(NfItemBase):
    pass


class NfItemUpdate(BaseModel):
    os_item_id:         Optional[int]   = None
    quantidade:         Optional[float] = None
    valor_unitario:     Optional[float] = None
    valor_total_item:   Optional[float] = None
    descricao_override: Optional[str]   = None


class NfItemResponse(NfItemBase):
    model_config = ConfigDict(from_attributes=True)
    id:    int
    nf_id: int


# ── NotaFiscal ───────────────────────────────────────────────────────
class NotaFiscalCreate(BaseModel):
    numero_nf:        Optional[str]  = None
    tipo_nf:          Literal["Produto", "Servico"]
    empresa_faturada: Optional[str]  = None
    fornecedor:       Optional[str]  = None
    valor_total_nf:   Optional[float] = None
    data_emissao:     Optional[date] = None
    observacoes:      Optional[str]  = None
    tipo_nf_needs_review: Optional[bool] = False
    itens:            list[NfItemCreate]    = []
    parcelas:         list[ParcelaCreate]   = []


class NotaFiscalUpdate(BaseModel):
    numero_nf:        Optional[str]  = None
    tipo_nf:          Optional[Literal["Produto", "Servico"]] = None
    empresa_faturada: Optional[str]  = None
    fornecedor:       Optional[str]  = None
    valor_total_nf:   Optional[float] = None
    data_emissao:     Optional[date] = None
    observacoes:      Optional[str]  = None
    tipo_nf_needs_review: Optional[bool] = None


class NotaFiscalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    os_id:            int
    numero_nf:        Optional[str]
    tipo_nf:          str
    empresa_faturada: Optional[str]
    fornecedor:       Optional[str]
    valor_total_nf:   Optional[float]
    data_emissao:     Optional[date]
    observacoes:      Optional[str]
    tipo_nf_needs_review: Optional[bool]
    criado_em:        Optional[datetime]
    itens:            list[NfItemResponse]  = []
    parcelas:         list[ParcelaResponse] = []


# ── OrdemServico ─────────────────────────────────────────────────────
class OsAbrir(BaseModel):
    id_veiculo:      int
    placa:           str
    modelo:          Optional[str]   = None
    empresa:         Optional[str]   = None
    id_contrato:     Optional[str]   = None
    implemento:      Optional[str]   = None
    fornecedor:      Optional[str]   = None
    tipo_manutencao: Optional[str]   = None
    categoria:       Optional[str]   = None
    responsavel_tec: Optional[str]   = None
    indisponivel:    bool            = True
    data_entrada:    Optional[date]  = None
    status_os:       str             = "em_andamento"
    km:              Optional[float] = None
    observacoes:     Optional[str]   = None
    itens:           list[OsItemCreate] = []


class OsUpdate(BaseModel):
    status_os:       Optional[str]          = None
    fornecedor:      Optional[str]          = None
    tipo_manutencao: Optional[str]          = None
    categoria:       Optional[str]          = None
    empresa:         Optional[str]          = None
    responsavel_tec: Optional[str]          = None
    indisponivel:    Optional[bool]         = None
    data_entrada:    Optional[date]         = None
    km:              Optional[float]        = None
    observacoes:     Optional[str]          = None
    itens:           Optional[list[OsItemEdit]] = None


class OsEditarFinalizada(BaseModel):
    """Edição completa de OS já finalizada (dados de execução + itens)."""
    data_execucao:   Optional[date]              = None
    km:              Optional[float]             = None
    prox_km:         Optional[float]             = None
    prox_data:       Optional[date]              = None
    responsavel_tec: Optional[str]               = None
    tipo_manutencao: Optional[str]               = None
    categoria:       Optional[str]               = None
    observacoes:     Optional[str]               = None
    itens:           Optional[list[OsItemEdit]]  = None


class OsExecutar(BaseModel):
    """Marca a OS como executada, aguardando NF."""
    data_execucao:     date
    km:                Optional[float] = None
    prox_km:           Optional[float] = None
    prox_data:         Optional[date]  = None
    status_execucao:   Optional[str]   = None
    descricao_pendente: Optional[str]  = None


class OsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:              int
    numero_os:       Optional[str]
    status_os:       str
    id_veiculo:      int
    placa:           Optional[str]
    modelo:          Optional[str]
    empresa:         Optional[str]
    id_contrato:     Optional[str]
    implemento:      Optional[str]
    fornecedor:      Optional[str]
    tipo_manutencao: Optional[str]
    categoria:       Optional[str]
    total_os:        Optional[float]
    responsavel_tec: Optional[str]
    indisponivel:    Optional[bool]
    km:                 Optional[float]
    data_entrada:       Optional[date]
    data_execucao:      Optional[date]
    prox_km:            Optional[float]
    prox_data:          Optional[date]
    status_execucao:    Optional[str]
    descricao_pendente: Optional[str]
    observacoes:        Optional[str]
    criado_em:          Optional[datetime]
    atualizado_em:      Optional[datetime]
    itens:              list[OsItemResponse]      = []
    notas_fiscais:      list[NotaFiscalResponse]  = []


# ── Merge assistido ──────────────────────────────────────────────────
class MergeSugestao(BaseModel):
    os_ids:        list[int]
    placa:         Optional[str]
    fornecedor:    Optional[str]
    id_ord_serv:   Optional[str]
    data_execucao: Optional[date]
    total_itens:   int
    total_nfs:     int
    motivos:       list[str]


class MergeRequest(BaseModel):
    os_ids:         list[int]
    os_destino_id:  int


# ── Auditoria ────────────────────────────────────────────────────────
class IntegridadeResponse(BaseModel):
    orfas: list[int]
    total: int
