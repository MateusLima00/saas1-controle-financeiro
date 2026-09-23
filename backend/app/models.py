import datetime as dt

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from .database import Base
from .timezone_utils import hoje


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)


class Session(Base):
    __tablename__ = "sessions"

    token = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    # Dono do registro (multi-tenant: cada usuário só vê os próprios
    # dados). Nullable por causa de bancos antigos com linhas anteriores
    # à migração — `run_light_migrations` faz o backfill pro primeiro
    # usuário existente, mas o código nunca deve criar uma linha nova
    # sem setar isso.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    banco = Column(String, nullable=False)
    tipo = Column(String, nullable=False)  # checking | savings | credit_card
    saldo = Column(Float, default=0)
    status = Column(String, default="connected")  # connected | error
    ultima_sync = Column(String, default="")
    origem = Column(String, default="manual")  # manual

    transacoes = relationship("Transaction", back_populates="conta")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    nome = Column(String, nullable=False)
    cor = Column(String, default="")
    regra = Column(String, default="")
    # Espelha os 4 blocos da planilha de equilíbrio financeiro (mais
    # "receita", que na planilha fica numa área separada mas segue a
    # mesma lógica de previsto x realizado por código).
    grupo = Column(String, default="fixo")  # receita | fixo | investimento | doacao | passivo
    previsto = Column(Float, default=0)  # valor orçado/planejado por mês (a "Previsto" da planilha)
    # Só usado quando grupo == "receita": identifica de qual provedor/
    # fonte de renda é (ex: "Provedor 1", "Provedor 2"), igual à planilha
    # que separa salário/vale/comissão por pessoa.
    provedor = Column(String, nullable=True)

    transacoes = relationship("Transaction", back_populates="categoria")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    data = Column(Date, nullable=False, default=hoje)
    descricao = Column(String, nullable=False)
    categoria_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    conta_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    valor = Column(Float, nullable=False)
    tipo = Column(String, nullable=False)  # debit | credit
    origem = Column(String, default="manual")  # manual | telegram | import
    # ATENÇÃO multi-tenant: esse `unique=True` é global (não é por
    # usuário) — ficou assim na migração leve porque sqlite não faz
    # DROP/ALTER de constraint sem recriar a tabela. Na prática, hoje é
    # só um usuário de verdade usando a importação de extrato, então o
    # risco de colisão entre usuários diferentes é baixo, mas se o app
    # ganhar mais gente importando extrato ativamente, isso precisa virar
    # um índice único composto (user_id, external_id).
    external_id = Column(String, nullable=True, unique=True, index=True)

    categoria = relationship("Category", back_populates="transacoes")
    conta = relationship("Account", back_populates="transacoes")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    nome = Column(String, nullable=False)
    tipo = Column(String, default="poupanca")  # poupanca | viagem
    icone = Column(String, default="PiggyBank")
    cor = Column(String, default="")
    valor_alvo = Column(Float, nullable=False)
    valor_atual = Column(Float, default=0)
    prazo = Column(String, nullable=True)

    historico = relationship(
        "GoalContribution", back_populates="meta", cascade="all, delete-orphan"
    )


class GoalContribution(Base):
    __tablename__ = "goal_contributions"

    id = Column(Integer, primary_key=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False)
    data = Column(Date, nullable=False, default=hoje)
    valor = Column(Float, nullable=False)

    meta = relationship("Goal", back_populates="historico")


class Investment(Base):
    __tablename__ = "investments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    nome = Column(String, nullable=False)
    tipo = Column(String, nullable=False)
    icone = Column(String, default="TrendingUp")
    cor = Column(String, default="")
    valor_investido = Column(Float, nullable=False)
    valor_atual = Column(Float, nullable=False)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    nome = Column(String, nullable=False)
    icone = Column(String, default="Cloud")
    cor = Column(String, default="")
    valor = Column(Float, nullable=False)
    ciclo = Column(String, default="Mensal")
    proxima_cobranca = Column(String, nullable=True)


class CompraParcelada(Base):
    __tablename__ = "compras_parceladas"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    descricao = Column(String, nullable=False)
    valor_total = Column(Float, nullable=False)
    num_parcelas = Column(Integer, nullable=False)
    conta_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    categoria_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    criada_em = Column(Date, nullable=False, default=hoje)

    conta = relationship("Account")
    categoria = relationship("Category")
    parcelas = relationship(
        "Parcela", back_populates="compra", cascade="all, delete-orphan", order_by="Parcela.numero"
    )


class Parcela(Base):
    __tablename__ = "parcelas"

    id = Column(Integer, primary_key=True)
    compra_id = Column(Integer, ForeignKey("compras_parceladas.id"), nullable=False)
    numero = Column(Integer, nullable=False)  # 1..num_parcelas
    valor = Column(Float, nullable=False)
    data_vencimento = Column(Date, nullable=False)
    # Preenchido quando a parcela vira uma transação de verdade (data de
    # vencimento chegou) — até lá é só um compromisso futuro, não conta em
    # nenhum saldo/gasto.
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)

    compra = relationship("CompraParcelada", back_populates="parcelas")
    transacao = relationship("Transaction")
