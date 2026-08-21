import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import require_service_token
from ..categorization import categoria_para_descricao
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
    data: dt.date
    descricao: str
    valor: float
    tipo: str
    categoria: str | None = None
    conta: str | None = None


class NeroResumoOut(BaseModel):
    saldoTotal: float
    gastoMes: float
    gastoMesAnterior: float
    contas: list[NeroContaResumoOut]
    gastosPorCategoria: list[schemas.GastoPorCategoriaOut]
    ultimasTransacoes: list[NeroTransacaoResumoOut]


@router.get("/nero/resumo", response_model=NeroResumoOut)
def resumo_para_nero(db: DbSession = Depends(get_db)):
    """Dado real do Saas1 (não o controle paralelo do Nero) — pro Nero
    responder no Telegram com números de verdade quando perguntarem
    "qual meu saldo" / "quanto gastei" etc."""
    resumo_geral = resumo(db)
    categorias = gastos_por_categoria(db)
    contas = db.query(models.Account).all()
    ultimas = (
        db.query(models.Transaction).order_by(models.Transaction.data.desc(), models.Transaction.id.desc()).limit(8).all()
    )
    return NeroResumoOut(
        saldoTotal=resumo_geral.saldoTotal,
        gastoMes=resumo_geral.gastoMes,
        gastoMesAnterior=resumo_geral.gastoMesAnterior,
        contas=[NeroContaResumoOut(banco=c.banco, tipo=c.tipo, saldo=c.saldo) for c in contas],
        gastosPorCategoria=categorias,
        ultimasTransacoes=[
            NeroTransacaoResumoOut(
                data=t.data,
                descricao=t.descricao,
                valor=t.valor,
                tipo=t.tipo,
                categoria=t.categoria.nome if t.categoria else None,
                conta=t.conta.banco if t.conta else None,
            )
            for t in ultimas
        ],
    )
