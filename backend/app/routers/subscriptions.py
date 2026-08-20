from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(
    prefix="/subscriptions", tags=["subscriptions"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=list[schemas.SubscriptionOut])
def list_subscriptions(db: DbSession = Depends(get_db)):
    return db.query(models.Subscription).all()


@router.post("", response_model=schemas.SubscriptionOut, status_code=201)
def create_subscription(payload: schemas.SubscriptionCreate, db: DbSession = Depends(get_db)):
    subscription = models.Subscription(**payload.model_dump())
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@router.put("/{subscription_id}", response_model=schemas.SubscriptionOut)
def update_subscription(
    subscription_id: int, payload: schemas.SubscriptionUpdate, db: DbSession = Depends(get_db)
):
    subscription = (
        db.query(models.Subscription).filter(models.Subscription.id == subscription_id).first()
    )
    if not subscription:
        raise HTTPException(404, "Assinatura não encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(subscription, field, value)
    db.commit()
    db.refresh(subscription)
    return subscription


@router.delete("/{subscription_id}", status_code=204)
def delete_subscription(subscription_id: int, db: DbSession = Depends(get_db)):
    subscription = (
        db.query(models.Subscription).filter(models.Subscription.id == subscription_id).first()
    )
    if not subscription:
        raise HTTPException(404, "Assinatura não encontrada")
    db.delete(subscription)
    db.commit()
