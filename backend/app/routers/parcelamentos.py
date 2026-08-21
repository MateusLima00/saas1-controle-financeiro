import calendar
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..services.parcelas import materializar_parcelas_vencidas
from ..timezone_utils import hoje as _hoje

router = APIRouter(
    prefix="/parcelamentos", tags=["parcelamentos"], dependencies=[Depends(get_current_user)]
)


def _somar_meses(data: dt.date, meses: int) -> dt.date:
    """Soma `meses` a `data`, cravando o dia no último dia do mês de
    destino se ele não existir (ex: 31/jan + 1 mês -> 28/fev, não 03/mar)."""
    mes_total = data.month - 1 + meses
    ano = data.year + mes_total // 12
    mes = mes_total % 12 + 1
    dia = min(data.day, calendar.monthrange(ano, mes)[1])
    return dt.date(ano, mes, dia)


def _parcela_out(p: models.Parcela) -> schemas.ParcelaOut:
    return schemas.ParcelaOut(
        id=p.id, numero=p.numero, valor=p.valor, data_vencimento=p.data_vencimento,
        paga=p.transaction_id is not None,
    )


def _compra_out(c: models.CompraParcelada) -> schemas.CompraParceladaOut:
    return schemas.CompraParceladaOut(
        id=c.id,
        descricao=c.descricao,
        valor_total=c.valor_total,
        num_parcelas=c.num_parcelas,
        conta_id=c.conta_id,
        conta=c.conta.banco if c.conta else None,
        categoria_id=c.categoria_id,
        categoria=c.categoria.nome if c.categoria else None,
        parcelas=[_parcela_out(p) for p in c.parcelas],
    )


@router.get("", response_model=list[schemas.CompraParceladaOut])
def list_parcelamentos(db: DbSession = Depends(get_db)):
    materializar_parcelas_vencidas(db)
    compras = db.query(models.CompraParcelada).order_by(models.CompraParcelada.id.desc()).all()
    return [_compra_out(c) for c in compras]


@router.post("", response_model=schemas.CompraParceladaOut, status_code=201)
def create_parcelamento(payload: schemas.CompraParceladaCreate, db: DbSession = Depends(get_db)):
    if payload.num_parcelas < 1:
        raise HTTPException(400, "Número de parcelas precisa ser pelo menos 1.")

    conta = db.query(models.Account).filter(models.Account.id == payload.conta_id).first()
    if not conta:
        raise HTTPException(404, "Conta (cartão) não encontrada.")

    compra = models.CompraParcelada(
        descricao=payload.descricao,
        valor_total=payload.valor_total,
        num_parcelas=payload.num_parcelas,
        conta_id=payload.conta_id,
        categoria_id=payload.categoria_id,
    )
    db.add(compra)
    db.flush()

    # Divide o valor total em parcelas iguais; o resto de arredondamento
    # (centavos) fica todo na última parcela, pra soma bater exatamente
    # com o valor total da compra.
    valor_parcela = round(payload.valor_total / payload.num_parcelas, 2)
    soma_parcial = 0.0
    for i in range(payload.num_parcelas):
        numero = i + 1
        if numero < payload.num_parcelas:
            valor = valor_parcela
            soma_parcial += valor
        else:
            valor = round(payload.valor_total - soma_parcial, 2)
        vencimento = _somar_meses(payload.data_primeira_parcela, i)
        db.add(
            models.Parcela(
                compra_id=compra.id, numero=numero, valor=valor, data_vencimento=vencimento
            )
        )

    db.commit()
    materializar_parcelas_vencidas(db)
    db.refresh(compra)
    return _compra_out(compra)


@router.delete("/{compra_id}", status_code=204)
def delete_parcelamento(compra_id: int, db: DbSession = Depends(get_db)):
    compra = db.query(models.CompraParcelada).filter(models.CompraParcelada.id == compra_id).first()
    if not compra:
        raise HTTPException(404, "Compra parcelada não encontrada.")

    # Parcelas já materializadas viraram transações de verdade — apaga
    # elas junto, senão ficariam órfãs no Extrato sem nenhum vínculo.
    ids_transacoes = [p.transaction_id for p in compra.parcelas if p.transaction_id]
    if ids_transacoes:
        db.query(models.Transaction).filter(models.Transaction.id.in_(ids_transacoes)).delete(
            synchronize_session=False
        )

    db.delete(compra)
    db.commit()


@router.get("/fatura", response_model=list[schemas.FaturaCartaoOut])
def fatura_cartoes(db: DbSession = Depends(get_db)):
    """Visão de fatura por cartão: o que já lançou esse mês (transações de
    verdade) + o que ainda vai lançar esse mês (parcelas futuras com
    vencimento dentro do mês atual, ainda não materializadas)."""
    materializar_parcelas_vencidas(db)
    hoje = _hoje()
    primeiro_dia = hoje.replace(day=1)
    ultimo_dia = hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1])

    cartoes = db.query(models.Account).filter(models.Account.tipo == "credit_card").all()
    resultado = []
    for cartao in cartoes:
        fechado = (
            db.query(func.coalesce(func.sum(models.Transaction.valor), 0))
            .filter(
                models.Transaction.conta_id == cartao.id,
                models.Transaction.tipo == "debit",
                models.Transaction.data >= primeiro_dia,
                models.Transaction.data <= ultimo_dia,
            )
            .scalar()
            or 0
        )
        pendente = (
            db.query(func.coalesce(func.sum(models.Parcela.valor), 0))
            .join(models.CompraParcelada, models.Parcela.compra_id == models.CompraParcelada.id)
            .filter(
                models.CompraParcelada.conta_id == cartao.id,
                models.Parcela.transaction_id.is_(None),
                models.Parcela.data_vencimento >= primeiro_dia,
                models.Parcela.data_vencimento <= ultimo_dia,
            )
            .scalar()
            or 0
        )
        resultado.append(
            schemas.FaturaCartaoOut(
                conta_id=cartao.id,
                conta=cartao.banco,
                totalFechado=abs(fechado),
                totalPendente=pendente,
                totalMes=abs(fechado) + pendente,
            )
        )
    return resultado
