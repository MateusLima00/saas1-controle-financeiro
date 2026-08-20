from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..services.notifications import notify_goal_achieved

router = APIRouter(
    prefix="/goals", tags=["goals"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=list[schemas.GoalOut])
def list_goals(db: DbSession = Depends(get_db)):
    return db.query(models.Goal).all()


@router.post("", response_model=schemas.GoalOut, status_code=201)
def create_goal(payload: schemas.GoalCreate, db: DbSession = Depends(get_db)):
    goal = models.Goal(**payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.put("/{goal_id}", response_model=schemas.GoalOut)
def update_goal(goal_id: int, payload: schemas.GoalUpdate, db: DbSession = Depends(get_db)):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(404, "Meta não encontrada")
    ja_batida_antes = goal.valor_atual >= goal.valor_alvo
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    if not ja_batida_antes and goal.valor_atual >= goal.valor_alvo:
        notify_goal_achieved(goal)
    return goal


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: int, db: DbSession = Depends(get_db)):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(404, "Meta não encontrada")
    db.delete(goal)
    db.commit()


@router.post("/{goal_id}/contributions", response_model=schemas.GoalOut, status_code=201)
def add_contribution(
    goal_id: int, payload: schemas.GoalContributionCreate, db: DbSession = Depends(get_db)
):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(404, "Meta não encontrada")
    ja_batida_antes = goal.valor_atual >= goal.valor_alvo
    contribuicao = models.GoalContribution(goal_id=goal_id, **payload.model_dump())
    goal.valor_atual = (goal.valor_atual or 0) + payload.valor
    db.add(contribuicao)
    db.commit()
    db.refresh(goal)
    if not ja_batida_antes and goal.valor_atual >= goal.valor_alvo:
        notify_goal_achieved(goal)
    return goal
