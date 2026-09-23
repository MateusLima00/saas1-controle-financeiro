from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..subscription_status import assinatura_ativa, data_fim_contrato
from ..timezone_utils import hoje as _hoje

router = APIRouter(
    prefix="/subscriptions", tags=["subscriptions"], dependencies=[Depends(get_current_user)]
)


def _subscription_out(assinatura: models.Subscription) -> schemas.SubscriptionOut:
    hoje = _hoje()
    return schemas.SubscriptionOut(
        id=assinatura.id,
        nome=assinatura.nome,
        icone=assinatura.icone,
        cor=assinatura.cor,
        valor=assinatura.valor,
        ciclo=assinatura.ciclo,
        proximaCobranca=assinatura.proxima_cobranca,
        dataInicio=assinatura.data_inicio,
        duracaoMeses=assinatura.duracao_meses,
        ativa=assinatura_ativa(assinatura, hoje),
        dataFim=data_fim_contrato(assinatura),
    )


@router.get("", response_model=list[schemas.SubscriptionOut])
def list_subscriptions(
    db: DbSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    incluir_expiradas: bool = False,
):
    """Por padrão só traz assinaturas ativas (mensais sem prazo, ou dentro
    do contrato) — um contrato de meses que já terminou some sozinho
    daqui, sem precisar apagar na mão (ver subscription_status.py).
    `?incluir_expiradas=true` traz tudo, usado pela tela de gerenciar
    assinaturas pra ainda dar pra ver/editar/renovar contratos encerrados."""
    assinaturas = db.query(models.Subscription).filter(models.Subscription.user_id == current_user.id).all()
    hoje = _hoje()
    if not incluir_expiradas:
        assinaturas = [a for a in assinaturas if assinatura_ativa(a, hoje)]
    return [_subscription_out(a) for a in assinaturas]


@router.post("", response_model=schemas.SubscriptionOut, status_code=201)
def create_subscription(
    payload: schemas.SubscriptionCreate,
    db: DbSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    dados = payload.model_dump()
    if not dados.get("data_inicio"):
        dados["data_inicio"] = _hoje()
    subscription = models.Subscription(**dados, user_id=current_user.id)
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return _subscription_out(subscription)


@router.put("/{subscription_id}", response_model=schemas.SubscriptionOut)
def update_subscription(
    subscription_id: int,
    payload: schemas.SubscriptionUpdate,
    db: DbSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    subscription = (
        db.query(models.Subscription)
        .filter(models.Subscription.id == subscription_id, models.Subscription.user_id == current_user.id)
        .first()
    )
    if not subscription:
        raise HTTPException(404, "Assinatura não encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(subscription, field, value)
    db.commit()
    db.refresh(subscription)
    return _subscription_out(subscription)


@router.delete("/{subscription_id}", status_code=204)
def delete_subscription(
    subscription_id: int,
    db: DbSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    subscription = (
        db.query(models.Subscription)
        .filter(models.Subscription.id == subscription_id, models.Subscription.user_id == current_user.id)
        .first()
    )
    if not subscription:
        raise HTTPException(404, "Assinatura não encontrada")
    db.delete(subscription)
    db.commit()
