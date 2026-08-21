import datetime as dt

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import require_service_token
from ..categorization import categoria_para_descricao
from ..database import get_db
from ..timezone_utils import hoje
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
