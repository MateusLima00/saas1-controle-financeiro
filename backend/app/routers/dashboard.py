import calendar
import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(
    prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)]
)


def _month_bounds(year: int, month: int) -> tuple[dt.date, dt.date]:
    first = dt.date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    last = dt.date(year, month, last_day)
    return first, last


def _sum_transacoes(db: DbSession, *, desde: dt.date | None = None, ate: dt.date | None = None) -> float:
    query = db.query(func.coalesce(func.sum(models.Transaction.valor), 0))
    if desde is not None:
        query = query.filter(models.Transaction.data >= desde)
    if ate is not None:
        query = query.filter(models.Transaction.data <= ate)
    return query.scalar() or 0


def _gasto_no_mes(db: DbSession, year: int, month: int) -> float:
    first, last = _month_bounds(year, month)
    total = (
        db.query(func.coalesce(func.sum(models.Transaction.valor), 0))
        .filter(
            models.Transaction.tipo == "debit",
            models.Transaction.data >= first,
            models.Transaction.data <= last,
        )
        .scalar()
    )
    return abs(total or 0)


def _saldo_ao_final_do_mes(db: DbSession, saldo_atual: float, year: int, month: int) -> float:
    _, last = _month_bounds(year, month)
    depois = _sum_transacoes(db, desde=last + dt.timedelta(days=1))
    return saldo_atual - depois


@router.get("/resumo", response_model=schemas.ResumoOut)
def resumo(db: DbSession = Depends(get_db)):
    hoje = dt.date.today()
    mes_anterior = hoje.month - 1 or 12
    ano_mes_anterior = hoje.year if hoje.month > 1 else hoje.year - 1

    saldo_total = db.query(func.coalesce(func.sum(models.Account.saldo), 0)).scalar() or 0
    gasto_mes = _gasto_no_mes(db, hoje.year, hoje.month)
    gasto_mes_anterior = _gasto_no_mes(db, ano_mes_anterior, mes_anterior)
    saldo_mes_anterior = _saldo_ao_final_do_mes(db, saldo_total, ano_mes_anterior, mes_anterior)

    ultima_conta = (
        db.query(models.Account)
        .filter(models.Account.ultima_sync != "")
        .order_by(models.Account.id.desc())
        .first()
    )

    return schemas.ResumoOut(
        saldoTotal=saldo_total,
        saldoMesAnterior=saldo_mes_anterior,
        gastoMes=gasto_mes,
        gastoMesAnterior=gasto_mes_anterior,
        ultimaSync=ultima_conta.ultima_sync if ultima_conta else "-",
    )


@router.get("/gastos-por-categoria", response_model=list[schemas.GastoPorCategoriaOut])
def gastos_por_categoria(db: DbSession = Depends(get_db)):
    hoje = dt.date.today()
    first, last = _month_bounds(hoje.year, hoje.month)

    linhas = (
        db.query(
            models.Category.nome,
            models.Category.cor,
            func.coalesce(func.sum(models.Transaction.valor), 0).label("total"),
        )
        .join(models.Transaction, models.Transaction.categoria_id == models.Category.id)
        .filter(
            models.Transaction.tipo == "debit",
            models.Transaction.data >= first,
            models.Transaction.data <= last,
        )
        .group_by(models.Category.id)
        .all()
    )
    return [
        schemas.GastoPorCategoriaOut(categoria=nome, valor=abs(total), cor=cor)
        for nome, cor, total in linhas
    ]


@router.get("/evolucao", response_model=list[schemas.EvolucaoMesOut])
def evolucao(db: DbSession = Depends(get_db), meses: int = 6):
    hoje = dt.date.today()
    saldo_total = db.query(func.coalesce(func.sum(models.Account.saldo), 0)).scalar() or 0

    meses_alvo: list[tuple[int, int]] = []
    y, m = hoje.year, hoje.month
    for _ in range(meses):
        meses_alvo.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    meses_alvo.reverse()

    resultado = []
    for ano, mes in meses_alvo:
        gasto = _gasto_no_mes(db, ano, mes)
        saldo = _saldo_ao_final_do_mes(db, saldo_total, ano, mes)
        resultado.append(
            schemas.EvolucaoMesOut(mes=dt.date(ano, mes, 1).strftime("%b"), saldo=saldo, gasto=gasto)
        )
    return resultado
