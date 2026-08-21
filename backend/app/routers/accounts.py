import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import get_current_user
from ..categorization import categoria_para_descricao
from ..database import get_db
from ..import_parsers import parse_csv, parse_ofx, parse_pdf
from ..timezone_utils import hoje

router = APIRouter(
    prefix="/accounts", tags=["accounts"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=list[schemas.AccountOut])
def list_accounts(db: DbSession = Depends(get_db)):
    return db.query(models.Account).all()


@router.post("", response_model=schemas.AccountOut, status_code=201)
def create_account(payload: schemas.AccountCreate, db: DbSession = Depends(get_db)):
    account = models.Account(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.put("/{account_id}", response_model=schemas.AccountOut)
def update_account(account_id: int, payload: schemas.AccountUpdate, db: DbSession = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Conta não encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int, db: DbSession = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Conta não encontrada")
    db.delete(account)
    db.commit()


@router.post("/{account_id}/import", response_model=schemas.ImportResultOut)
async def import_extrato(account_id: int, file: UploadFile, db: DbSession = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Conta não encontrada")

    nome = (file.filename or "").lower()
    conteudo = await file.read()

    try:
        if nome.endswith(".ofx") or nome.endswith(".qfx"):
            transacoes = parse_ofx(conteudo, account_id)
        elif nome.endswith(".csv"):
            transacoes = parse_csv(conteudo, account_id)
        elif nome.endswith(".pdf"):
            transacoes = parse_pdf(conteudo, account_id)
        else:
            raise HTTPException(
                400, "Formato não suportado. Envie um arquivo .csv, .ofx, .qfx ou .pdf."
            )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    importadas = 0
    duplicadas = 0
    for t in transacoes:
        existente = (
            db.query(models.Transaction)
            .filter(models.Transaction.external_id == t.external_id)
            .first()
        )
        if existente:
            duplicadas += 1
            continue
        categoria = categoria_para_descricao(db, t.descricao)
        db.add(
            models.Transaction(
                data=dt.date.fromisoformat(t.data),
                descricao=t.descricao,
                categoria_id=categoria.id if categoria else None,
                valor=t.valor,
                tipo=t.tipo,
                conta_id=account_id,
                origem="import",
                external_id=t.external_id,
            )
        )
        importadas += 1

    account.ultima_sync = hoje().isoformat()
    db.commit()

    return schemas.ImportResultOut(
        importadas=importadas,
        duplicadas=duplicadas,
        ignoradas=len(transacoes) - importadas - duplicadas,
    )
