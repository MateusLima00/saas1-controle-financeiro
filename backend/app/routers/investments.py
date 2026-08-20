from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(
    prefix="/investments", tags=["investments"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=list[schemas.InvestmentOut])
def list_investments(db: DbSession = Depends(get_db)):
    return db.query(models.Investment).all()


@router.post("", response_model=schemas.InvestmentOut, status_code=201)
def create_investment(payload: schemas.InvestmentCreate, db: DbSession = Depends(get_db)):
    investment = models.Investment(**payload.model_dump())
    db.add(investment)
    db.commit()
    db.refresh(investment)
    return investment


@router.put("/{investment_id}", response_model=schemas.InvestmentOut)
def update_investment(
    investment_id: int, payload: schemas.InvestmentUpdate, db: DbSession = Depends(get_db)
):
    investment = db.query(models.Investment).filter(models.Investment.id == investment_id).first()
    if not investment:
        raise HTTPException(404, "Investimento não encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(investment, field, value)
    db.commit()
    db.refresh(investment)
    return investment


@router.delete("/{investment_id}", status_code=204)
def delete_investment(investment_id: int, db: DbSession = Depends(get_db)):
    investment = db.query(models.Investment).filter(models.Investment.id == investment_id).first()
    if not investment:
        raise HTTPException(404, "Investimento não encontrado")
    db.delete(investment)
    db.commit()
