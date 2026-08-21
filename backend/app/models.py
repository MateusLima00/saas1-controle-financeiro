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
    banco = Column(String, nullable=False)
    tipo = Column(String, nullable=False)  # checking | savings | credit_card
    saldo = Column(Float, default=0)
    status = Column(String, default="connected")  # connected | error
    ultima_sync = Column(String, default="")
    origem = Column(String, default="manual")  # pluggy | manual
    pluggy_item_id = Column(String, nullable=True, index=True)
    pluggy_account_id = Column(String, nullable=True, unique=True, index=True)

    transacoes = relationship("Transaction", back_populates="conta")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    cor = Column(String, default="")
    regra = Column(String, default="")

    transacoes = relationship("Transaction", back_populates="categoria")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    data = Column(Date, nullable=False, default=hoje)
    descricao = Column(String, nullable=False)
    categoria_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    conta_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    valor = Column(Float, nullable=False)
    tipo = Column(String, nullable=False)  # debit | credit
    origem = Column(String, default="manual")  # pluggy | manual | telegram | import
    external_id = Column(String, nullable=True, unique=True, index=True)

    categoria = relationship("Category", back_populates="transacoes")
    conta = relationship("Account", back_populates="transacoes")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True)
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
    nome = Column(String, nullable=False)
    tipo = Column(String, nullable=False)
    icone = Column(String, default="TrendingUp")
    cor = Column(String, default="")
    valor_investido = Column(Float, nullable=False)
    valor_atual = Column(Float, nullable=False)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    icone = Column(String, default="Cloud")
    cor = Column(String, default="")
    valor = Column(Float, nullable=False)
    ciclo = Column(String, default="Mensal")
    proxima_cobranca = Column(String, nullable=True)
