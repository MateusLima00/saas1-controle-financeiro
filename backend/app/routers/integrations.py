import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import get_owner_user_id, require_service_token
from ..categorization import categoria_para_descricao, extrair_palavra_chave
from ..database import get_db
from ..services.import_service import importar_extrato
from ..services.notifications import notify_goal_achieved
from ..subscription_status import assinatura_ativa
from ..timezone_utils import hoje
from .transactions import _to_out

router = APIRouter(
    prefix="/integrations",
    tags=["integrations"],
    dependencies=[Depends(require_service_token)],
)


def _owner_id_ou_erro(db: DbSession) -> int:
    """A integração Nero é pessoal (um token de serviço só, sem login de
    usuário) — sempre opera sobre os dados do dono original da conta,
    mesmo que outras pessoas criem conta própria no app depois."""
    owner_id = get_owner_user_id(db)
    if owner_id is None:
        raise HTTPException(404, "Nenhum usuário cadastrado ainda no Saas1.")
    return owner_id


class NeroTransactionIn(BaseModel):
    descricao: str
    valor: float
    tipo: str  # debit | credit
    data: dt.date | None = None


@router.post("/nero/transactions", response_model=schemas.TransactionOut, status_code=201)
def criar_transacao_do_nero(payload: NeroTransactionIn, db: DbSession = Depends(get_db)):
    owner_id = _owner_id_ou_erro(db)
    categoria = categoria_para_descricao(db, payload.descricao, owner_id)
    valor = payload.valor if payload.tipo == "credit" else -abs(payload.valor)
    transacao = models.Transaction(
        data=payload.data or hoje(),
        descricao=payload.descricao,
        valor=valor,
        tipo=payload.tipo,
        categoria_id=categoria.id if categoria else None,
        origem="nero",
        user_id=owner_id,
    )
    db.add(transacao)
    db.commit()
    db.refresh(transacao)
    return _to_out(transacao)


class NeroAccountOut(BaseModel):
    id: int
    banco: str
    tipo: str


@router.get("/nero/accounts", response_model=list[NeroAccountOut])
def listar_contas_para_nero(db: DbSession = Depends(get_db)):
    """Pro Nero conseguir perguntar/confirmar qual conta é qual banco
    antes de mandar um extrato pra importar (ver POST .../import abaixo)."""
    owner_id = _owner_id_ou_erro(db)
    contas = db.query(models.Account).filter(models.Account.user_id == owner_id).all()
    return [NeroAccountOut(id=c.id, banco=c.banco, tipo=c.tipo) for c in contas]


@router.post("/nero/accounts/{account_id}/import", response_model=schemas.ImportResultOut)
async def importar_extrato_do_nero(account_id: int, file: UploadFile, db: DbSession = Depends(get_db)):
    """Mesmo comportamento de `POST /accounts/{id}/import`, só que
    autenticado por token de serviço (Nero) em vez de sessão de navegador
    — o usuário manda o extrato pro bot no Telegram, o Nero identifica a
    conta pela conversa e chama isso aqui."""
    owner_id = _owner_id_ou_erro(db)
    account = (
        db.query(models.Account)
        .filter(models.Account.id == account_id, models.Account.user_id == owner_id)
        .first()
    )
    if not account:
        raise HTTPException(404, "Conta não encontrada")
    conteudo = await file.read()
    return importar_extrato(db, account, file.filename or "", conteudo)


class NeroContaResumoOut(BaseModel):
    banco: str
    tipo: str
    saldo: float


class NeroTransacaoResumoOut(BaseModel):
    id: int
    data: dt.date
    descricao: str
    valor: float
    tipo: str
    categoria: str | None = None
    conta: str | None = None


class NeroUltimosPorContaOut(BaseModel):
    conta: str
    transacoes: list[NeroTransacaoResumoOut]


class NeroResumoOut(BaseModel):
    saldoTotal: float
    gastoMes: float
    gastoMesAnterior: float
    contas: list[NeroContaResumoOut]
    gastosPorCategoria: list[schemas.GastoPorCategoriaOut]
    ultimosPorConta: list[NeroUltimosPorContaOut]


def _transacao_para_nero(t: models.Transaction) -> NeroTransacaoResumoOut:
    # Descrição enxuta pra exibição no chat — a mesma extração usada pra
    # aprender regra de categoria (remove "Pix enviado:", "Cp:12345-" etc,
    # deixando só quem pagou/recebeu).
    return NeroTransacaoResumoOut(
        id=t.id,
        data=t.data,
        descricao=extrair_palavra_chave(t.descricao),
        valor=t.valor,
        tipo=t.tipo,
        categoria=t.categoria.nome if t.categoria else None,
        conta=t.conta.banco if t.conta else None,
    )


@router.get("/nero/resumo", response_model=NeroResumoOut)
def resumo_para_nero(db: DbSession = Depends(get_db)):
    """Dado real do Saas1 (não o controle paralelo do Nero) — pro Nero
    responder no Telegram com números de verdade quando perguntarem
    "qual meu saldo" / "quanto gastei" etc. Últimos lançamentos vêm
    agrupados por conta (poucos de cada, não só os N mais recentes de
    qualquer banco — senão um banco movimentado engole os outros).

    Calcula tudo localmente (em vez de chamar as funções do router de
    dashboard) porque elas dependem de `current_user` via sessão de
    navegador — aqui só existe o token de serviço, então usamos sempre o
    dono original (`_owner_id_ou_erro`)."""
    from . import dashboard as dashboard_router

    owner_id = _owner_id_ou_erro(db)
    hoje_dt = hoje()
    mes_anterior = hoje_dt.month - 1 or 12
    ano_mes_anterior = hoje_dt.year if hoje_dt.month > 1 else hoje_dt.year - 1

    contas = db.query(models.Account).filter(models.Account.user_id == owner_id).all()
    saldo_total = sum(c.saldo or 0 for c in contas)
    gasto_mes = dashboard_router._gasto_no_mes(db, owner_id, hoje_dt.year, hoje_dt.month)
    gasto_mes_anterior = dashboard_router._gasto_no_mes(db, owner_id, ano_mes_anterior, mes_anterior)

    first, last = dashboard_router._month_bounds(hoje_dt.year, hoje_dt.month)
    linhas_categoria = (
        db.query(
            models.Category.nome,
            models.Category.cor,
            models.Transaction.valor,
        )
        .join(models.Transaction, models.Transaction.categoria_id == models.Category.id)
        .filter(
            models.Category.user_id == owner_id,
            models.Transaction.user_id == owner_id,
            models.Transaction.tipo == "debit",
            models.Transaction.data >= first,
            models.Transaction.data <= last,
        )
        .all()
    )
    totais_categoria: dict[tuple[str, str], float] = {}
    for nome, cor, valor in linhas_categoria:
        totais_categoria[(nome, cor)] = totais_categoria.get((nome, cor), 0) + abs(valor)
    categorias = [
        schemas.GastoPorCategoriaOut(categoria=nome, valor=valor, cor=cor)
        for (nome, cor), valor in totais_categoria.items()
    ]

    ultimos_por_conta = []
    for conta in contas:
        transacoes = (
            db.query(models.Transaction)
            .filter(models.Transaction.conta_id == conta.id, models.Transaction.user_id == owner_id)
            .order_by(models.Transaction.data.desc(), models.Transaction.id.desc())
            .limit(3)
            .all()
        )
        if transacoes:
            ultimos_por_conta.append(
                NeroUltimosPorContaOut(conta=conta.banco, transacoes=[_transacao_para_nero(t) for t in transacoes])
            )

    sem_conta = (
        db.query(models.Transaction)
        .filter(models.Transaction.conta_id.is_(None), models.Transaction.user_id == owner_id)
        .order_by(models.Transaction.data.desc(), models.Transaction.id.desc())
        .limit(3)
        .all()
    )
    if sem_conta:
        ultimos_por_conta.append(
            NeroUltimosPorContaOut(conta="Dinheiro", transacoes=[_transacao_para_nero(t) for t in sem_conta])
        )

    return NeroResumoOut(
        saldoTotal=saldo_total,
        gastoMes=gasto_mes,
        gastoMesAnterior=gasto_mes_anterior,
        contas=[NeroContaResumoOut(banco=c.banco, tipo=c.tipo, saldo=c.saldo) for c in contas],
        gastosPorCategoria=categorias,
        ultimosPorConta=ultimos_por_conta,
    )


# -- Consultas extras (metas, assinaturas, parcelas, categorias) --------


class NeroMetaOut(BaseModel):
    id: int
    nome: str
    valorAtual: float
    valorAlvo: float
    prazo: str | None = None


def _meta_para_nero(m: models.Goal) -> NeroMetaOut:
    return NeroMetaOut(id=m.id, nome=m.nome, valorAtual=m.valor_atual, valorAlvo=m.valor_alvo, prazo=m.prazo)


@router.get("/nero/metas", response_model=list[NeroMetaOut])
def listar_metas_para_nero(db: DbSession = Depends(get_db)):
    owner_id = _owner_id_ou_erro(db)
    metas = db.query(models.Goal).filter(models.Goal.user_id == owner_id).all()
    return [_meta_para_nero(m) for m in metas]


class NeroMetaCreateIn(BaseModel):
    nome: str
    valorAlvo: float
    prazo: str | None = None


@router.post("/nero/metas", response_model=NeroMetaOut, status_code=201)
def criar_meta_do_nero(payload: NeroMetaCreateIn, db: DbSession = Depends(get_db)):
    owner_id = _owner_id_ou_erro(db)
    meta = models.Goal(
        nome=payload.nome, valor_alvo=payload.valorAlvo, valor_atual=0, prazo=payload.prazo, user_id=owner_id
    )
    db.add(meta)
    db.commit()
    db.refresh(meta)
    return _meta_para_nero(meta)


class NeroMetaAporteIn(BaseModel):
    valor: float


@router.post("/nero/metas/{meta_id}/aportes", response_model=NeroMetaOut)
def aportar_meta_do_nero(meta_id: int, payload: NeroMetaAporteIn, db: DbSession = Depends(get_db)):
    owner_id = _owner_id_ou_erro(db)
    meta = db.query(models.Goal).filter(models.Goal.id == meta_id, models.Goal.user_id == owner_id).first()
    if not meta:
        raise HTTPException(404, "Meta não encontrada")
    ja_batida_antes = meta.valor_atual >= meta.valor_alvo
    meta.valor_atual = (meta.valor_atual or 0) + payload.valor
    db.add(models.GoalContribution(goal_id=meta.id, valor=payload.valor))
    db.commit()
    db.refresh(meta)
    if not ja_batida_antes and meta.valor_atual >= meta.valor_alvo:
        notify_goal_achieved(db, meta)
    return _meta_para_nero(meta)


@router.delete("/nero/metas/{meta_id}", status_code=204)
def apagar_meta_do_nero(meta_id: int, db: DbSession = Depends(get_db)):
    owner_id = _owner_id_ou_erro(db)
    meta = db.query(models.Goal).filter(models.Goal.id == meta_id, models.Goal.user_id == owner_id).first()
    if not meta:
        raise HTTPException(404, "Meta não encontrada")
    db.delete(meta)
    db.commit()


class NeroAssinaturaOut(BaseModel):
    nome: str
    valor: float
    ciclo: str
    proximaCobranca: str | None = None


@router.get("/nero/assinaturas", response_model=list[NeroAssinaturaOut])
def listar_assinaturas_para_nero(db: DbSession = Depends(get_db)):
    owner_id = _owner_id_ou_erro(db)
    hoje_dt = hoje()
    assinaturas = db.query(models.Subscription).filter(models.Subscription.user_id == owner_id).all()
    return [
        NeroAssinaturaOut(nome=a.nome, valor=a.valor, ciclo=a.ciclo, proximaCobranca=a.proxima_cobranca)
        for a in assinaturas
        if assinatura_ativa(a, hoje_dt)
    ]


class NeroParcelaOut(BaseModel):
    compra: str
    numero: int
    numParcelas: int
    valor: float
    dataVencimento: dt.date
    conta: str


@router.get("/nero/parcelas", response_model=list[NeroParcelaOut])
def listar_parcelas_pendentes_para_nero(db: DbSession = Depends(get_db)):
    """Só as parcelas AINDA NÃO lançadas (vencimento futuro) — as já
    materializadas em transação de verdade já aparecem no resumo normal."""
    owner_id = _owner_id_ou_erro(db)
    parcelas = (
        db.query(models.Parcela)
        .join(models.CompraParcelada, models.Parcela.compra_id == models.CompraParcelada.id)
        .filter(models.Parcela.transaction_id.is_(None), models.CompraParcelada.user_id == owner_id)
        .order_by(models.Parcela.data_vencimento)
        .all()
    )
    return [
        NeroParcelaOut(
            compra=p.compra.descricao,
            numero=p.numero,
            numParcelas=p.compra.num_parcelas,
            valor=p.valor,
            dataVencimento=p.data_vencimento,
            conta=p.compra.conta.banco if p.compra.conta else "?",
        )
        for p in parcelas
    ]


class NeroCategoryOut(BaseModel):
    id: int
    nome: str


@router.get("/nero/categorias", response_model=list[NeroCategoryOut])
def listar_categorias_para_nero(db: DbSession = Depends(get_db)):
    """Pro Nero conseguir casar o nome que a pessoa falar ("muda pra
    Alimentação") com o categoria_id de verdade, ao editar uma transação."""
    owner_id = _owner_id_ou_erro(db)
    categorias = db.query(models.Category).filter(models.Category.user_id == owner_id).all()
    return [NeroCategoryOut(id=c.id, nome=c.nome) for c in categorias]


class NeroTransactionUpdateIn(BaseModel):
    descricao: str | None = None
    valor: float | None = None
    categoria_id: int | None = None


@router.put("/nero/transactions/{transaction_id}", response_model=schemas.TransactionOut)
def editar_transacao_do_nero(
    transaction_id: int, payload: NeroTransactionUpdateIn, db: DbSession = Depends(get_db)
):
    owner_id = _owner_id_ou_erro(db)
    transacao = (
        db.query(models.Transaction)
        .filter(models.Transaction.id == transaction_id, models.Transaction.user_id == owner_id)
        .first()
    )
    if not transacao:
        raise HTTPException(404, "Transação não encontrada")
    dados = payload.model_dump(exclude_unset=True)
    for campo, valor in dados.items():
        setattr(transacao, campo, valor)
    db.commit()
    db.refresh(transacao)
    return _to_out(transacao)


@router.delete("/nero/transactions/{transaction_id}", status_code=204)
def apagar_transacao_do_nero(transaction_id: int, db: DbSession = Depends(get_db)):
    owner_id = _owner_id_ou_erro(db)
    transacao = (
        db.query(models.Transaction)
        .filter(models.Transaction.id == transaction_id, models.Transaction.user_id == owner_id)
        .first()
    )
    if not transacao:
        raise HTTPException(404, "Transação não encontrada")
    db.delete(transacao)
    db.commit()
