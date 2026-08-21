import datetime as dt

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# -- Auth ---------------------------------------------------------------


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class GoogleLoginRequest(BaseModel):
    credential: str


class MeResponse(BaseModel):
    email: EmailStr


# -- Accounts -------------------------------------------------------------


class AccountBase(BaseModel):
    banco: str
    tipo: str
    saldo: float = 0
    status: str = "connected"
    ultima_sync: str = Field("", serialization_alias="ultimaSync", validation_alias="ultimaSync")
    origem: str = "manual"

    model_config = ConfigDict(populate_by_name=True)


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    banco: str | None = None
    tipo: str | None = None
    saldo: float | None = None
    status: str | None = None
    ultima_sync: str | None = Field(None, serialization_alias="ultimaSync", validation_alias="ultimaSync")
    origem: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class AccountOut(AccountBase):
    id: int

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


# -- Categories -------------------------------------------------------------


class CategoryBase(BaseModel):
    nome: str
    cor: str = ""
    regra: str = ""


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    nome: str | None = None
    cor: str | None = None
    regra: str | None = None


class CategoryOut(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# -- Transactions -------------------------------------------------------------


class TransactionBase(BaseModel):
    data: dt.date
    descricao: str
    categoria_id: int | None = None
    conta_id: int | None = None
    valor: float
    tipo: str
    origem: str = "manual"
    external_id: str | None = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    data: dt.date | None = None
    descricao: str | None = None
    categoria_id: int | None = None
    conta_id: int | None = None
    valor: float | None = None
    tipo: str | None = None
    origem: str | None = None


class TransactionOut(TransactionBase):
    id: int
    categoria: str | None = None
    conta: str | None = None

    model_config = ConfigDict(from_attributes=True)


# -- Goals -------------------------------------------------------------


class GoalContributionBase(BaseModel):
    data: dt.date
    valor: float


class GoalContributionCreate(GoalContributionBase):
    pass


class GoalContributionOut(GoalContributionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class GoalBase(BaseModel):
    nome: str
    tipo: str = "poupanca"
    icone: str = "PiggyBank"
    cor: str = ""
    valor_alvo: float = Field(serialization_alias="valorAlvo", validation_alias="valorAlvo")
    valor_atual: float = Field(0, serialization_alias="valorAtual", validation_alias="valorAtual")
    prazo: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    nome: str | None = None
    tipo: str | None = None
    icone: str | None = None
    cor: str | None = None
    valor_alvo: float | None = Field(None, serialization_alias="valorAlvo", validation_alias="valorAlvo")
    valor_atual: float | None = Field(None, serialization_alias="valorAtual", validation_alias="valorAtual")
    prazo: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class GoalOut(GoalBase):
    id: int
    historico: list[GoalContributionOut] = []

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


# -- Investments -------------------------------------------------------------


class InvestmentBase(BaseModel):
    nome: str
    tipo: str
    icone: str = "TrendingUp"
    cor: str = ""
    valor_investido: float = Field(serialization_alias="valorInvestido", validation_alias="valorInvestido")
    valor_atual: float = Field(serialization_alias="valorAtual", validation_alias="valorAtual")

    model_config = ConfigDict(populate_by_name=True)


class InvestmentCreate(InvestmentBase):
    pass


class InvestmentUpdate(BaseModel):
    nome: str | None = None
    tipo: str | None = None
    icone: str | None = None
    cor: str | None = None
    valor_investido: float | None = Field(None, serialization_alias="valorInvestido", validation_alias="valorInvestido")
    valor_atual: float | None = Field(None, serialization_alias="valorAtual", validation_alias="valorAtual")

    model_config = ConfigDict(populate_by_name=True)


class InvestmentOut(InvestmentBase):
    id: int

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


# -- Subscriptions -------------------------------------------------------------


class SubscriptionBase(BaseModel):
    nome: str
    icone: str = "Cloud"
    cor: str = ""
    valor: float
    ciclo: str = "Mensal"
    proxima_cobranca: str | None = Field(None, serialization_alias="proximaCobranca", validation_alias="proximaCobranca")

    model_config = ConfigDict(populate_by_name=True)


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    nome: str | None = None
    icone: str | None = None
    cor: str | None = None
    valor: float | None = None
    ciclo: str | None = None
    proxima_cobranca: str | None = Field(None, serialization_alias="proximaCobranca", validation_alias="proximaCobranca")

    model_config = ConfigDict(populate_by_name=True)


class SubscriptionOut(SubscriptionBase):
    id: int

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


# -- Import / Sync -------------------------------------------------------------


class ImportResultOut(BaseModel):
    importadas: int
    duplicadas: int
    ignoradas: int


# -- Dashboard aggregates -------------------------------------------------------------


class ResumoOut(BaseModel):
    saldoTotal: float
    saldoMesAnterior: float
    gastoMes: float
    gastoMesAnterior: float
    ultimaSync: str


class GastoPorCategoriaOut(BaseModel):
    categoria: str
    valor: float
    cor: str


class EvolucaoMesOut(BaseModel):
    mes: str
    saldo: float
    gasto: float
