from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, Date, DateTime, Text,
    ForeignKey, func,
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
    manutencao_id = Column(Integer, ForeignKey("manutencoes.id"), nullable=False)

    nf_ordem         = Column(Integer)
    nota             = Column(String(50))
    data_vencimento  = Column(Date)
    parcela_atual    = Column(Integer)
    parcela_total    = Column(Integer)
    valor_parcela    = Column(Numeric(14, 2))
    forma_pgto       = Column(String(50))
    status_pagamento = Column(String(20), default="Pendente")  # Pago | Pendente

    manutencao = relationship("Manutencao", back_populates="parcelas")


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
