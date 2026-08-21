import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import require_service_token
from ..categorization import categoria_para_descricao, extrair_palavra_chave
from ..database import get_db
from ..services.import_service import importar_extrato
from ..timezone_utils import hoje
from .dashboard import gastos_por_categoria, resumo
from .transactions import _to_out

router = APIRouter(
    prefix="/integrations",
    tags=["integrations"],
    dependencies=[Depends(require_service_token)],
)


class NeroTransactionIn(BaseModel):
    descricao: str
    valor: float
    tipo: str  # debit | credit
    data: dt.date | None = None


@router.post("/nero/transactions", response_model=schemas.TransactionOut, status_code=201)
def criar_transacao_do_nero(payload: NeroTransactionIn, db: DbSession = Depends(get_db)):
    categoria = categoria_para_descricao(db, payload.descricao)
    valor = payload.valor if payload.tipo == "credit" else -abs(payload.valor)
    transacao = models.Transaction(
        data=payload.data or hoje(),
        descricao=payload.descricao,
        valor=valor,
        tipo=payload.tipo,
        categoria_id=categoria.id if categoria else None,
        origem="nero",
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
    contas = db.query(models.Account).all()
    return [NeroAccountOut(id=c.id, banco=c.banco, tipo=c.tipo) for c in contas]


@router.post("/nero/accounts/{account_id}/import", response_model=schemas.ImportResultOut)
async def importar_extrato_do_nero(account_id: int, file: UploadFile, db: DbSession = Depends(get_db)):
    """Mesmo comportamento de `POST /accounts/{id}/import`, só que
    autenticado por token de serviço (Nero) em vez de sessão de navegador
    — o usuário manda o extrato pro bot no Telegram, o Nero identifica a
    conta pela conversa e chama isso aqui."""
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
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
    qualquer banco — senão um banco movimentado engole os outros)."""
    resumo_geral = resumo(db)
    categorias = gastos_por_categoria(db)
    contas = db.query(models.Account).all()

    ultimos_por_conta = []
    for conta in contas:
        transacoes = (
            db.query(models.Transaction)
            .filter(models.Transaction.conta_id == conta.id)
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
        .filter(models.Transaction.conta_id.is_(None))
        .order_by(models.Transaction.data.desc(), models.Transaction.id.desc())
        .limit(3)
        .all()
    )
    if sem_conta:
        ultimos_por_conta.append(
            NeroUltimosPorContaOut(conta="Dinheiro", transacoes=[_transacao_para_nero(t) for t in sem_conta])
        )

    return NeroResumoOut(
        saldoTotal=resumo_geral.saldoTotal,
        gastoMes=resumo_geral.gastoMes,
        gastoMesAnterior=resumo_geral.gastoMesAnterior,
        contas=[NeroContaResumoOut(banco=c.banco, tipo=c.tipo, saldo=c.saldo) for c in contas],
        gastosPorCategoria=categorias,
        ultimosPorConta=ultimos_por_conta,
    )


# -- Consultas extras (metas, assinaturas, parcelas, categorias) --------


class NeroMetaOut(BaseModel):
    nome: str
    valorAtual: float
    valorAlvo: float
    prazo: str | None = None


@router.get("/nero/metas", response_model=list[NeroMetaOut])
def listar_metas_para_nero(db: DbSession = Depends(get_db)):
    metas = db.query(models.Goal).all()
    return [
        NeroMetaOut(nome=m.nome, valorAtual=m.valor_atual, valorAlvo=m.valor_alvo, prazo=m.prazo) for m in metas
    ]


class NeroAssinaturaOut(BaseModel):
    nome: str
    valor: float
    ciclo: str
    proximaCobranca: str | None = None


@router.get("/nero/assinaturas", response_model=list[NeroAssinaturaOut])
def listar_assinaturas_para_nero(db: DbSession = Depends(get_db)):
    assinaturas = db.query(models.Subscription).all()
    return [
        NeroAssinaturaOut(nome=a.nome, valor=a.valor, ciclo=a.ciclo, proximaCobranca=a.proxima_cobranca)
        for a in assinaturas
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
    parcelas = (
        db.query(models.Parcela)
        .filter(models.Parcela.transaction_id.is_(None))
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
    categorias = db.query(models.Category).all()
    return [NeroCategoryOut(id=c.id, nome=c.nome) for c in categorias]


class NeroTransactionUpdateIn(BaseModel):
    descricao: str | None = None
    valor: float | None = None
    categoria_id: int | None = None


@router.put("/nero/transactions/{transaction_id}", response_model=schemas.TransactionOut)
def editar_transacao_do_nero(
    transaction_id: int, payload: NeroTransactionUpdateIn, db: DbSession = Depends(get_db)
):
    transacao = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
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
    transacao = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not transacao:
        raise HTTPException(404, "Transação não encontrada")
    db.delete(transacao)
    db.commit()
