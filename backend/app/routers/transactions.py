import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(
    prefix="/transactions", tags=["transactions"], dependencies=[Depends(get_current_user)]
)


def _to_out(t: models.Transaction) -> schemas.TransactionOut:
    return schemas.TransactionOut(
        id=t.id,
        data=t.data,
        descricao=t.descricao,
        categoria_id=t.categoria_id,
        conta_id=t.conta_id,
        valor=t.valor,
        tipo=t.tipo,
        origem=t.origem,
        categoria=t.categoria.nome if t.categoria else None,
        conta=t.conta.banco if t.conta else None,
    )


@router.get("", response_model=list[schemas.TransactionOut])
def list_transactions(
    db: DbSession = Depends(get_db),
    de: dt.date | None = None,
    ate: dt.date | None = None,
    conta_id: int | None = None,
):
    query = db.query(models.Transaction)
    if de is not None:
        query = query.filter(models.Transaction.data >= de)
    if ate is not None:
        query = query.filter(models.Transaction.data <= ate)
    if conta_id is not None:
        query = query.filter(models.Transaction.conta_id == conta_id)
    transacoes = query.order_by(models.Transaction.data.desc()).all()
    return [_to_out(t) for t in transacoes]


@router.post("", response_model=schemas.TransactionOut, status_code=201)
def create_transaction(payload: schemas.TransactionCreate, db: DbSession = Depends(get_db)):
    transacao = models.Transaction(**payload.model_dump())
    db.add(transacao)
    db.commit()
    db.refresh(transacao)
    return _to_out(transacao)


@router.put("/{transaction_id}", response_model=schemas.TransactionOut)
def update_transaction(
    transaction_id: int, payload: schemas.TransactionUpdate, db: DbSession = Depends(get_db)
):
    transacao = (
        db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    )
    if not transacao:
        raise HTTPException(404, "Transação não encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(transacao, field, value)
    db.commit()
    db.refresh(transacao)
    return _to_out(transacao)


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: int, db: DbSession = Depends(get_db)):
    transacao = (
        db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    )
    if not transacao:
        raise HTTPException(404, "Transação não encontrada")
    db.delete(transacao)
    db.commit()
