import calendar
import datetime as dt
import os

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..services.notifications import _cobrancas_do_dia, _gasto_incomum
from ..subscription_status import assinatura_ativa
from ..timezone_utils import hoje as _hoje


def _float_env(nome: str, default: float) -> float:
    try:
        return float(os.getenv(nome, str(default)))
    except ValueError:
        return default


LOW_BALANCE_THRESHOLD = _float_env("LOW_BALANCE_THRESHOLD", 0)
UNUSUAL_SPEND_MULTIPLIER = _float_env("UNUSUAL_SPEND_MULTIPLIER", 2)
DIAS_ALERTA_CONTA = 3

router = APIRouter(
    prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)]
)


def _month_bounds(year: int, month: int) -> tuple[dt.date, dt.date]:
    first = dt.date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    last = dt.date(year, month, last_day)
    return first, last


def _sum_transacoes(
    db: DbSession, user_id: int, *, desde: dt.date | None = None, ate: dt.date | None = None
) -> float:
    query = db.query(func.coalesce(func.sum(models.Transaction.valor), 0)).filter(
        models.Transaction.user_id == user_id
    )
    if desde is not None:
        query = query.filter(models.Transaction.data >= desde)
    if ate is not None:
        query = query.filter(models.Transaction.data <= ate)
    return query.scalar() or 0


def _gasto_no_mes(db: DbSession, user_id: int, year: int, month: int) -> float:
    first, last = _month_bounds(year, month)
    total = (
        db.query(func.coalesce(func.sum(models.Transaction.valor), 0))
        .filter(
            models.Transaction.user_id == user_id,
            models.Transaction.tipo == "debit",
            models.Transaction.data >= first,
            models.Transaction.data <= last,
        )
        .scalar()
    )
    return abs(total or 0)


def _saldo_ao_final_do_mes(db: DbSession, user_id: int, saldo_atual: float, year: int, month: int) -> float:
    _, last = _month_bounds(year, month)
    depois = _sum_transacoes(db, user_id, desde=last + dt.timedelta(days=1))
    return saldo_atual - depois


@router.get("/resumo", response_model=schemas.ResumoOut)
def resumo(db: DbSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    hoje = _hoje()
    mes_anterior = hoje.month - 1 or 12
    ano_mes_anterior = hoje.year if hoje.month > 1 else hoje.year - 1

    saldo_total = (
        db.query(func.coalesce(func.sum(models.Account.saldo), 0))
        .filter(models.Account.user_id == current_user.id)
        .scalar()
        or 0
    )
    gasto_mes = _gasto_no_mes(db, current_user.id, hoje.year, hoje.month)
    gasto_mes_anterior = _gasto_no_mes(db, current_user.id, ano_mes_anterior, mes_anterior)
    saldo_mes_anterior = _saldo_ao_final_do_mes(db, current_user.id, saldo_total, ano_mes_anterior, mes_anterior)

    ultima_conta = (
        db.query(models.Account)
        .filter(models.Account.user_id == current_user.id, models.Account.ultima_sync != "")
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
def gastos_por_categoria(db: DbSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    hoje = _hoje()
    first, last = _month_bounds(hoje.year, hoje.month)

    linhas = (
        db.query(
            models.Category.nome,
            models.Category.cor,
            func.coalesce(func.sum(models.Transaction.valor), 0).label("total"),
        )
        .join(models.Transaction, models.Transaction.categoria_id == models.Category.id)
        .filter(
            models.Category.user_id == current_user.id,
            models.Transaction.user_id == current_user.id,
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


@router.get("/orcamento", response_model=list[schemas.OrcamentoGrupoOut])
def orcamento(
    db: DbSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    ano: int | None = None,
    mes: int | None = None,
):
    """Previsto x Realizado por categoria, agrupado (receita/fixo/
    investimento/doacao/passivo) — o mesmo que a área central da planilha
    de equilíbrio financeiro: cada categoria tem um valor Previsto (fixo,
    cadastrado na categoria) e um Realizado (soma automática das
    transações do mês daquela categoria, equivalente ao SUMIF da
    planilha)."""
    hoje = _hoje()
    ano = ano or hoje.year
    mes = mes or hoje.month
    first, last = _month_bounds(ano, mes)

    realizado_por_categoria = dict(
        db.query(
            models.Transaction.categoria_id,
            func.coalesce(func.sum(func.abs(models.Transaction.valor)), 0),
        )
        .filter(
            models.Transaction.user_id == current_user.id,
            models.Transaction.data >= first,
            models.Transaction.data <= last,
        )
        .group_by(models.Transaction.categoria_id)
        .all()
    )

    categorias = (
        db.query(models.Category)
        .filter(models.Category.user_id == current_user.id)
        .order_by(models.Category.grupo, models.Category.nome)
        .all()
    )

    grupos: dict[str, list[schemas.OrcamentoCategoriaOut]] = {}
    for categoria in categorias:
        realizado = realizado_por_categoria.get(categoria.id, 0) or 0
        grupos.setdefault(categoria.grupo or "fixo", []).append(
            schemas.OrcamentoCategoriaOut(
                categoriaId=categoria.id,
                categoria=categoria.nome,
                cor=categoria.cor,
                grupo=categoria.grupo or "fixo",
                previsto=categoria.previsto or 0,
                realizado=realizado,
            )
        )

    ordem_grupos = ["receita", "fixo", "investimento", "doacao", "passivo"]
    resultado = []
    for grupo in ordem_grupos:
        itens = grupos.pop(grupo, [])
        if not itens:
            continue
        resultado.append(
            schemas.OrcamentoGrupoOut(
                grupo=grupo,
                previsto=sum(c.previsto for c in itens),
                realizado=sum(c.realizado for c in itens),
                categorias=itens,
            )
        )
    # Qualquer grupo fora da lista conhecida (categoria antiga sem grupo
    # válido) ainda aparece, só entra depois dos grupos padrão.
    for grupo, itens in grupos.items():
        resultado.append(
            schemas.OrcamentoGrupoOut(
                grupo=grupo,
                previsto=sum(c.previsto for c in itens),
                realizado=sum(c.realizado for c in itens),
                categorias=itens,
            )
        )
    return resultado


@router.get("/saldo-periodo", response_model=schemas.SaldoPeriodoOut)
def saldo_periodo(
    db: DbSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    ano: int | None = None,
    mes: int | None = None,
):
    """Saldo = Receita realizada - Despesa realizada do mês (fórmula
    `=F17-F24` da planilha), calculado a partir das categorias com
    grupo="receita" vs os demais grupos — diferente de `/resumo`, que
    mostra o saldo em conta (patrimônio), não o fluxo do mês."""
    hoje = _hoje()
    ano = ano or hoje.year
    mes = mes or hoje.month
    first, last = _month_bounds(ano, mes)

    def _soma(grupo_filtro):
        previsto = (
            db.query(func.coalesce(func.sum(models.Category.previsto), 0))
            .filter(models.Category.user_id == current_user.id, grupo_filtro)
            .scalar()
            or 0
        )
        realizado = (
            db.query(func.coalesce(func.sum(func.abs(models.Transaction.valor)), 0))
            .join(models.Category, models.Transaction.categoria_id == models.Category.id)
            .filter(
                models.Category.user_id == current_user.id,
                models.Transaction.user_id == current_user.id,
                grupo_filtro,
                models.Transaction.data >= first,
                models.Transaction.data <= last,
            )
            .scalar()
            or 0
        )
        return previsto, realizado

    receita_previsto, receita_realizado = _soma(models.Category.grupo == "receita")
    despesa_previsto, despesa_realizado = _soma(models.Category.grupo != "receita")

    return schemas.SaldoPeriodoOut(
        receitaPrevista=receita_previsto,
        receitaRealizada=receita_realizado,
        despesaPrevista=despesa_previsto,
        despesaRealizada=despesa_realizado,
        saldo=receita_realizado - despesa_realizado,
    )


@router.get("/evolucao", response_model=list[schemas.EvolucaoMesOut])
def evolucao(
    db: DbSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    meses: int = 6,
):
    hoje = _hoje()
    saldo_total = (
        db.query(func.coalesce(func.sum(models.Account.saldo), 0))
        .filter(models.Account.user_id == current_user.id)
        .scalar()
        or 0
    )

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
        gasto = _gasto_no_mes(db, current_user.id, ano, mes)
        saldo = _saldo_ao_final_do_mes(db, current_user.id, saldo_total, ano, mes)
        resultado.append(
            schemas.EvolucaoMesOut(mes=dt.date(ano, mes, 1).strftime("%b"), saldo=saldo, gasto=gasto)
        )
    return resultado


@router.get("/notificacoes", response_model=list[schemas.NotificacaoOut])
def notificacoes(db: DbSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Sino de notificação: as mesmas regras que já disparam email
    (contas a vencer, saldo baixo, gasto incomum de ontem), calculadas na
    hora — não depende do email ter sido enviado/configurado, e não some
    depois de ler (não temos "marcar como lida" ainda, é sempre o estado
    atual)."""
    hoje = _hoje()
    itens: list[schemas.NotificacaoOut] = []

    for dias in range(DIAS_ALERTA_CONTA + 1):
        data_alvo = hoje + dt.timedelta(days=dias)
        for principal, secundaria in _cobrancas_do_dia(db, current_user.id, data_alvo):
            quando = "hoje" if dias == 0 else "amanhã" if dias == 1 else f"em {dias} dias"
            itens.append(
                schemas.NotificacaoOut(
                    id=f"conta:{data_alvo.isoformat()}:{principal}",
                    tipo="conta_a_vencer",
                    titulo=principal,
                    mensagem=f"{secundaria} · vence {quando}",
                    urgente=dias <= 1,
                )
            )

    contas_baixas = (
        db.query(models.Account)
        .filter(models.Account.user_id == current_user.id, models.Account.saldo < LOW_BALANCE_THRESHOLD)
        .all()
    )
    for conta in contas_baixas:
        itens.append(
            schemas.NotificacaoOut(
                id=f"saldo:{conta.id}",
                tipo="saldo_baixo",
                titulo=f"Saldo baixo — {conta.banco}",
                mensagem=f"R$ {conta.saldo:.2f}",
                urgente=True,
            )
        )

    ontem = hoje - dt.timedelta(days=1)
    aviso_gasto = _gasto_incomum(db, current_user.id, hoje, ontem)
    if aviso_gasto:
        itens.append(
            schemas.NotificacaoOut(
                id=f"gasto-incomum:{ontem.isoformat()}",
                tipo="gasto_incomum",
                titulo="Gasto acima do normal ontem",
                mensagem=aviso_gasto.split("\n")[0].removeprefix("📈 "),
            )
        )

    return itens
