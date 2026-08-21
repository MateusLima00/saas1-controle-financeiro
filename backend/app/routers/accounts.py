from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..services.import_service import importar_extrato

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
    conteudo = await file.read()
    return importar_extrato(db, account, file.filename or "", conteudo)
