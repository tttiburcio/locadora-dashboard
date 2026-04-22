from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, Date, DateTime, Text,
    ForeignKey, Index, CheckConstraint, func,
)
from sqlalchemy.orm import relationship
from database import Base


# ─────────────────────────────────────────────
# FROTA
# ─────────────────────────────────────────────
class Frota(Base):
    __tablename__ = "frota"

    id          = Column(Integer, primary_key=True)   # IDVeiculo original
    placa       = Column(String(20), unique=True, nullable=False)
    empresa     = Column(String(100))
    marca       = Column(String(80))
    modelo      = Column(String(100))
    status      = Column(String(50))
    tipagem     = Column(String(80))
    implemento  = Column(String(80))
    valor_total = Column(Numeric(14, 2))

    manutencoes = relationship("Manutencao", back_populates="veiculo")


# ─────────────────────────────────────────────
# MANUTENÇÃO — uma linha por OS
# ─────────────────────────────────────────────
class Manutencao(Base):
    __tablename__ = "manutencoes"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Workflow ──────────────────────────────
    # aberta | em_andamento | aguardando_peca | finalizada
    status_manutencao = Column(String(30), nullable=False, default="aberta")

    # ── Identificação do veículo (desnormalizado para agilidade) ──
    id_veiculo  = Column(Integer, ForeignKey("frota.id"), nullable=False)
    placa       = Column(String(20))
    modelo      = Column(String(100))
    empresa     = Column(String(100))
    id_contrato = Column(String(50))
    implemento  = Column(String(80))

    # ── Dados da OS ──────────────────────────
    id_ord_serv    = Column(String(50))          # gerado na finalização
    valida_nova_os = Column(String(10))
    total_os       = Column(Numeric(14, 2))      # preenchido na finalização
    categoria      = Column(String(30))          # Serviço | Compra
    fornecedor     = Column(String(120))
    tipo_manutencao = Column(String(30))         # Preventiva | Corretiva
    sistema        = Column(String(80))
    servico        = Column(String(200))
    descricao      = Column(Text)
    qtd_itens      = Column(Integer)

    # ── KM e pneus ────────────────────────────
    km             = Column(Numeric(10, 0))
    posicao_pneu   = Column(String(50))
    qtd_pneu       = Column(Integer)
    espec_pneu     = Column(String(100))
    marca_pneu     = Column(String(80))
    manejo_pneu    = Column(String(80))

    # ── Controle operacional ──────────────────
    responsavel_tec = Column(String(80))
    indisponivel    = Column(Boolean, default=False)
    data_entrada    = Column(Date)               # NOVO: entrada p/ manutenção
    data_execucao   = Column(Date)               # data de execução / conclusão

    # ── Próxima manutenção ────────────────────
    prox_km   = Column(Numeric(10, 0))
    prox_data = Column(Date)

    observacoes = Column(Text)

    criado_em     = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    veiculo  = relationship("Frota", back_populates="manutencoes")
    parcelas = relationship(
        "ManutencaoParcela",
        back_populates="manutencao",
        cascade="all, delete-orphan",
    )


# ─────────────────────────────────────────────
# PARCELAS DE PAGAMENTO — uma linha por parcela
# ─────────────────────────────────────────────
class ManutencaoParcela(Base):
    __tablename__ = "manutencao_parcelas"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    manutencao_id = Column(Integer, ForeignKey("manutencoes.id"), nullable=True)

    nf_ordem         = Column(Integer)
    nota             = Column(String(50))
    fornecedor       = Column(String(120))
    valor_item_total = Column(Numeric(14, 2))
    tipo_custo       = Column(String(30))
    data_vencimento  = Column(Date)
    parcela_atual    = Column(Integer)
    parcela_total    = Column(Integer)
    valor_parcela    = Column(Numeric(14, 2))
    forma_pgto       = Column(String(50))
    status_pagamento = Column(String(20), default="Pendente")  # Pago | Pendente

    # Prorrogação
    data_vencimento_original = Column(Date)
    prorrogada               = Column(Boolean, default=False)
    isento_encargos          = Column(Boolean)
    tipo_pgto_prorrogacao    = Column(String(20))   # boleto | pix
    chave_pix                = Column(String(100))
    multa_pct                = Column(Numeric(6, 2))
    juros_diario_pct         = Column(Numeric(6, 4))
    data_prevista_pagamento  = Column(Date)
    dias_cartorio            = Column(Integer)
    valor_atualizado         = Column(Numeric(14, 2))

    # Reembolso (preparação para aba futura)
    sera_reembolsado    = Column(Boolean, default=False)
    valor_reembolso     = Column(Numeric(14, 2))
    qtd_itens_reembolso = Column(Integer)
    motivo_reembolso    = Column(Text)

    # ── Vínculo novo modelo (nf_id autoritativo; manutencao_id legado) ──
    nf_id       = Column(Integer, ForeignKey("notas_fiscais.id"), nullable=True)
    deletado_em = Column(DateTime, nullable=True)   # soft delete

    manutencao  = relationship("Manutencao", back_populates="parcelas")
    nota_fiscal = relationship("NotaFiscal", back_populates="parcelas")

    __table_args__ = (
        Index("idx_parcela_nf", "nf_id"),
        Index("idx_parcela_venc", "data_vencimento"),
    )


# ─────────────────────────────────────────────
# FATURAMENTO UNITÁRIO (receita por veículo/mês)
# ─────────────────────────────────────────────
class FatUnitario(Base):
    __tablename__ = "fat_unitario"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    mes         = Column(Date)
    id_veiculo  = Column(Integer, ForeignKey("frota.id"))
    contrato    = Column(String(100))
    medicao     = Column(Numeric(14, 2))
    trabalhado  = Column(Integer)
    parado      = Column(Integer)


# ─────────────────────────────────────────────
# REEMBOLSOS
# ─────────────────────────────────────────────
class Reembolso(Base):
    __tablename__ = "reembolsos"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    emissao          = Column(Date)
    id_veiculo       = Column(Integer, ForeignKey("frota.id"))
    valor_reembolso  = Column(Numeric(14, 2))


# ─────────────────────────────────────────────
# FATURAMENTO GERAL (NF emitidas)
# ─────────────────────────────────────────────
class Faturamento(Base):
    __tablename__ = "faturamento"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    emissao         = Column(Date)
    valor_locacoes  = Column(Numeric(14, 2))
    valor_recebido  = Column(Numeric(14, 2))


# ─────────────────────────────────────────────
# SEGURO MENSAL
# ─────────────────────────────────────────────
class SeguroMensal(Base):
    __tablename__ = "seguro_mensal"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    vencimento = Column(Date)
    id_veiculo = Column(Integer, ForeignKey("frota.id"))
    valor      = Column(Numeric(14, 2))


# ─────────────────────────────────────────────
# IMPOSTOS
# ─────────────────────────────────────────────
class Imposto(Base):
    __tablename__ = "impostos"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    ano_imposto      = Column(Integer)
    id_veiculo       = Column(Integer, ForeignKey("frota.id"))
    valor_total_final = Column(Numeric(14, 2))


# ─────────────────────────────────────────────
# RASTREAMENTO
# ─────────────────────────────────────────────
class Rastreamento(Base):
    __tablename__ = "rastreamento"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    vencimento = Column(Date)
    id_veiculo = Column(Integer, ForeignKey("frota.id"))
    valor      = Column(Numeric(14, 2))


# ─────────────────────────────────────────────
# NOVO MODELO HIERÁRQUICO: OS → Itens → NFs → Itens da NF → Parcelas
# ─────────────────────────────────────────────
class OrdemServico(Base):
    __tablename__ = "ordens_servico"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    numero_os   = Column(String(50), nullable=True, unique=True)  # gerado na 1ª NF
    status_os   = Column(String(40), nullable=False, default="em_andamento")
    # aberta | em_andamento | aguardando_peca | executado_aguardando_nf | finalizada

    id_veiculo  = Column(Integer, ForeignKey("frota.id"), nullable=False)
    placa       = Column(String(20))
    modelo      = Column(String(100))
    empresa     = Column(String(100))
    id_contrato = Column(String(50))
    implemento  = Column(String(80))

    fornecedor      = Column(String(120))
    tipo_manutencao = Column(String(30))
    categoria       = Column(String(30))
    total_os        = Column(Numeric(14, 2))
    responsavel_tec = Column(String(80))
    indisponivel    = Column(Boolean, default=False)

    km                 = Column(Numeric(10, 0))
    data_entrada       = Column(Date)
    data_execucao      = Column(Date)
    prox_km            = Column(Numeric(10, 0))
    prox_data          = Column(Date)
    status_execucao    = Column(String(40))
    descricao_pendente = Column(Text)
    observacoes        = Column(Text)

    deletado_em     = Column(DateTime, nullable=True)
    criado_em       = Column(DateTime, server_default=func.now())
    atualizado_em   = Column(DateTime, server_default=func.now(), onupdate=func.now())
    migrado_de_ids  = Column(Text)  # JSON list[int]

    veiculo       = relationship("Frota")
    itens         = relationship("OsItem", back_populates="os", cascade="all, delete-orphan")
    notas_fiscais = relationship("NotaFiscal", back_populates="os")  # sem cascade (financeiro)

    __table_args__ = (
        Index("idx_os_veiculo_data", "id_veiculo", "data_execucao"),
        Index("idx_os_status", "status_os"),
        Index("idx_os_numero", "numero_os"),
    )


class OsItem(Base):
    __tablename__ = "os_itens"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    os_id     = Column(Integer, ForeignKey("ordens_servico.id"), nullable=False)

    categoria = Column(String(30))
    sistema   = Column(String(80))
    servico   = Column(String(200))
    descricao = Column(Text)
    qtd_itens = Column(Integer)

    posicao_pneu = Column(String(50))
    qtd_pneu     = Column(Integer)
    espec_pneu   = Column(String(100))
    marca_pneu   = Column(String(80))
    manejo_pneu  = Column(String(80))

    criado_em = Column(DateTime, server_default=func.now())
    manutencao_origem_id = Column(Integer, nullable=True)  # rastreabilidade de migração

    os       = relationship("OrdemServico", back_populates="itens")
    nf_itens = relationship("NfItem", back_populates="os_item")

    __table_args__ = (Index("idx_osi_os", "os_id"),)


class NotaFiscal(Base):
    __tablename__ = "notas_fiscais"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    os_id          = Column(Integer, ForeignKey("ordens_servico.id"), nullable=False)

    numero_nf        = Column(String(50))
    tipo_nf          = Column(String(20), nullable=False)  # Produto | Servico
    empresa_faturada = Column(String(100))
    fornecedor       = Column(String(120))
    valor_total_nf   = Column(Numeric(14, 2))
    data_emissao     = Column(Date)
    observacoes      = Column(Text)

    tipo_nf_needs_review = Column(Boolean, default=False)
    deletado_em          = Column(DateTime, nullable=True)
    criado_em            = Column(DateTime, server_default=func.now())
    nf_ordem_origem      = Column(Integer, nullable=True)

    os       = relationship("OrdemServico", back_populates="notas_fiscais")
    itens    = relationship("NfItem", back_populates="nota_fiscal", cascade="all, delete-orphan")
    parcelas = relationship("ManutencaoParcela", back_populates="nota_fiscal")

    __table_args__ = (
        CheckConstraint("tipo_nf IN ('Produto','Servico')", name="ck_tipo_nf"),
        Index("idx_nf_os", "os_id"),
        Index("idx_nf_emissao", "data_emissao"),
    )


class NfItem(Base):
    __tablename__ = "nf_itens"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    nf_id       = Column(Integer, ForeignKey("notas_fiscais.id"), nullable=False)
    os_item_id  = Column(Integer, ForeignKey("os_itens.id"), nullable=False)

    quantidade         = Column(Numeric(14, 4), default=1)
    valor_unitario     = Column(Numeric(14, 2))
    valor_total_item   = Column(Numeric(14, 2))
    descricao_override = Column(Text)

    criado_em = Column(DateTime, server_default=func.now())

    nota_fiscal = relationship("NotaFiscal", back_populates="itens")
    os_item     = relationship("OsItem", back_populates="nf_itens")

    __table_args__ = (
        Index("idx_nfitem_nf", "nf_id"),
        Index("idx_nfitem_osi", "os_item_id"),
    )


class OsCounter(Base):
    """Gerador atômico de numero_os por ano. UPSERT garante concorrência segura."""
    __tablename__ = "os_counters"

    ano    = Column(Integer, primary_key=True)
    ultimo = Column(Integer, nullable=False, default=0)
