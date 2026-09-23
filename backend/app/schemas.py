import datetime as dt

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# -- Auth ---------------------------------------------------------------


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class SignupRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=6)


class SolicitarRecuperacaoRequest(BaseModel):
    email: EmailStr


class ConfirmarRecuperacaoRequest(BaseModel):
    email: EmailStr
    codigo: str
    senha_nova: str = Field(min_length=6, serialization_alias="senhaNova", validation_alias="senhaNova")

    model_config = ConfigDict(populate_by_name=True)


class TrocarSenhaRequest(BaseModel):
    senha_atual: str = Field(serialization_alias="senhaAtual", validation_alias="senhaAtual")
    senha_nova: str = Field(min_length=6, serialization_alias="senhaNova", validation_alias="senhaNova")

    model_config = ConfigDict(populate_by_name=True)


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
    grupo: str = "fixo"  # receita | fixo | investimento | doacao | passivo
    previsto: float = 0  # orçamento mensal dessa categoria
    provedor: str | None = None  # só relevante quando grupo == "receita"


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    nome: str | None = None
    cor: str | None = None
    regra: str | None = None
    grupo: str | None = None
    previsto: float | None = None
    provedor: str | None = None


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
    # Contrato por prazo fixo (ex: 12 meses) em vez de mensal indefinida —
    # None = sem prazo (comportamento de sempre). Ver subscription_status.py.
    data_inicio: dt.date | None = Field(None, serialization_alias="dataInicio", validation_alias="dataInicio")
    duracao_meses: int | None = Field(None, serialization_alias="duracaoMeses", validation_alias="duracaoMeses")

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
    data_inicio: dt.date | None = Field(None, serialization_alias="dataInicio", validation_alias="dataInicio")
    duracao_meses: int | None = Field(None, serialization_alias="duracaoMeses", validation_alias="duracaoMeses")

    model_config = ConfigDict(populate_by_name=True)


class SubscriptionOut(SubscriptionBase):
    id: int
    ativa: bool = True
    data_fim: dt.date | None = Field(None, serialization_alias="dataFim", validation_alias="dataFim")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


# -- Compras parceladas -------------------------------------------------------------


class ParcelaOut(BaseModel):
    id: int
    numero: int
    valor: float
    data_vencimento: dt.date = Field(serialization_alias="dataVencimento", validation_alias="dataVencimento")
    paga: bool

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CompraParceladaCreate(BaseModel):
    descricao: str
    valor_total: float = Field(serialization_alias="valorTotal", validation_alias="valorTotal")
    num_parcelas: int = Field(serialization_alias="numParcelas", validation_alias="numParcelas")
    conta_id: int = Field(serialization_alias="contaId", validation_alias="contaId")
    categoria_id: int | None = Field(None, serialization_alias="categoriaId", validation_alias="categoriaId")
    data_primeira_parcela: dt.date = Field(
        serialization_alias="dataPrimeiraParcela", validation_alias="dataPrimeiraParcela"
    )

    model_config = ConfigDict(populate_by_name=True)


class CompraParceladaOut(BaseModel):
    id: int
    descricao: str
    valor_total: float = Field(serialization_alias="valorTotal", validation_alias="valorTotal")
    num_parcelas: int = Field(serialization_alias="numParcelas", validation_alias="numParcelas")
    conta_id: int = Field(serialization_alias="contaId", validation_alias="contaId")
    conta: str | None = None
    categoria_id: int | None = Field(None, serialization_alias="categoriaId", validation_alias="categoriaId")
    categoria: str | None = None
    parcelas: list[ParcelaOut] = []

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class FaturaCartaoOut(BaseModel):
    conta_id: int = Field(serialization_alias="contaId", validation_alias="contaId")
    conta: str
    totalFechado: float  # transações do mês já lançadas (materializadas) nesse cartão
    totalPendente: float  # parcelas futuras com vencimento no mês, ainda não materializadas
    totalMes: float  # soma dos dois — visão de "quanto vai fechar esse mês"

    model_config = ConfigDict(populate_by_name=True)


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


# -- Orçamento (Previsto x Realizado, igual ao modelo da planilha) ------------


class OrcamentoCategoriaOut(BaseModel):
    categoriaId: int
    categoria: str
    cor: str
    grupo: str
    previsto: float
    realizado: float


class OrcamentoGrupoOut(BaseModel):
    grupo: str
    previsto: float
    realizado: float
    categorias: list[OrcamentoCategoriaOut]


class NotificacaoOut(BaseModel):
    """Item do sino de notificação — as mesmas regras que já disparam
    email (dashboard.py: contas a vencer, saldo baixo, gasto incomum),
    só que calculadas na hora pra exibir no dropdown, sem depender de
    email ter sido configurado/entregue."""

    id: str
    tipo: str  # conta_a_vencer | saldo_baixo | gasto_incomum
    titulo: str
    mensagem: str
    urgente: bool = False


class SaldoPeriodoOut(BaseModel):
    """Saldo = Receita realizada - Despesa realizada do mês, igual à
    fórmula `=F17-F24` da planilha (linha RECEITAS menos linha DESPESAS)."""

    receitaPrevista: float
    receitaRealizada: float
    despesaPrevista: float
    despesaRealizada: float
    saldo: float
