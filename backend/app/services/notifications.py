"""Regras de quando disparar email pro usuário. Cada checagem é
independente e nunca propaga exceção — notificação não pode derrubar o
sync nem nenhuma outra rota (ver `email_service.send_email`).

Gatilhos implementados:
- Falha de sincronização (chamado direto do job diário).
- Meta atingida (chamado direto do router de goals, ao criar contribuição
  ou editar valor_atual).
- Resumo diário + saldo baixo/negativo + assinatura próxima de cobrar +
  transação grande + gasto incomum do dia — tudo junto num só email
  ("dígest diário"), rodado pelo job depois do sync (`run_daily_digest`).
"""
import datetime as dt
import logging
import os

from sqlalchemy import func
from sqlalchemy.orm import Session as DbSession

from .. import models
from .email_service import send_email

logger = logging.getLogger(__name__)


def _float_env(nome: str, default: float) -> float:
    try:
        return float(os.getenv(nome, str(default)))
    except ValueError:
        return default


LOW_BALANCE_THRESHOLD = _float_env("LOW_BALANCE_THRESHOLD", 0)
LARGE_TRANSACTION_THRESHOLD = _float_env("LARGE_TRANSACTION_THRESHOLD", 500)
SUBSCRIPTION_ALERT_DAYS = int(_float_env("SUBSCRIPTION_ALERT_DAYS", 3))
UNUSUAL_SPEND_MULTIPLIER = _float_env("UNUSUAL_SPEND_MULTIPLIER", 2)


def notify_sync_failure(item_id: str, erro: str) -> None:
    send_email(
        "⚠️ Falha na sincronização com a Pluggy",
        f"O sync automático do item {item_id} falhou hoje ({dt.date.today().isoformat()}).\n\n"
        f"Erro: {erro}\n\n"
        "Verifique se o banco continua conectado (tela Contas) — pode ser "
        "necessário reconectar pelo widget.",
    )


def notify_goal_achieved(goal: "models.Goal") -> None:
    send_email(
        f"🎉 Meta atingida: {goal.nome}",
        f"Sua meta \"{goal.nome}\" bateu o valor alvo!\n\n"
        f"Valor atual: R$ {goal.valor_atual:.2f}\n"
        f"Valor alvo: R$ {goal.valor_alvo:.2f}",
    )


def run_daily_digest(db: DbSession) -> None:
    try:
        hoje = dt.date.today()
        ontem = hoje - dt.timedelta(days=1)

        partes = [_resumo(db)]

        contas_baixas = _contas_saldo_baixo(db)
        if contas_baixas:
            partes.append(contas_baixas)

        assinaturas = _assinaturas_proximas(db, hoje)
        if assinaturas:
            partes.append(assinaturas)

        transacoes_grandes = _transacoes_grandes(db, ontem)
        if transacoes_grandes:
            partes.append(transacoes_grandes)

        gasto_incomum = _gasto_incomum(db, hoje, ontem)
        if gasto_incomum:
            partes.append(gasto_incomum)

        corpo = "\n\n".join(partes)
        send_email(f"📊 Resumo financeiro — {hoje.strftime('%d/%m/%Y')}", corpo)
    except Exception:
        logger.exception("Falha ao montar o dígest diário de notificações.")


def _resumo(db: DbSession) -> str:
    saldo_total = db.query(func.coalesce(func.sum(models.Account.saldo), 0)).scalar() or 0
    hoje = dt.date.today()
    inicio_mes = hoje.replace(day=1)
    gasto_mes = (
        db.query(func.coalesce(func.sum(models.Transaction.valor), 0))
        .filter(
            models.Transaction.tipo == "debit",
            models.Transaction.data >= inicio_mes,
            models.Transaction.data <= hoje,
        )
        .scalar()
    )
    return f"Saldo total: R$ {saldo_total:.2f}\nGasto no mês: R$ {abs(gasto_mes or 0):.2f}"


def _contas_saldo_baixo(db: DbSession) -> str | None:
    contas = (
        db.query(models.Account)
        .filter(models.Account.saldo < LOW_BALANCE_THRESHOLD)
        .all()
    )
    if not contas:
        return None
    linhas = "\n".join(f"- {c.banco}: R$ {c.saldo:.2f}" for c in contas)
    return f"⚠️ Contas com saldo baixo (< R$ {LOW_BALANCE_THRESHOLD:.2f}):\n{linhas}"


def _assinaturas_proximas(db: DbSession, hoje: dt.date) -> str | None:
    limite = (hoje + dt.timedelta(days=SUBSCRIPTION_ALERT_DAYS)).isoformat()
    assinaturas = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.proxima_cobranca.isnot(None),
            models.Subscription.proxima_cobranca >= hoje.isoformat(),
            models.Subscription.proxima_cobranca <= limite,
        )
        .all()
    )
    if not assinaturas:
        return None
    linhas = "\n".join(
        f"- {a.nome}: R$ {a.valor:.2f} em {a.proxima_cobranca}" for a in assinaturas
    )
    return f"📅 Assinaturas cobrando nos próximos {SUBSCRIPTION_ALERT_DAYS} dias:\n{linhas}"


def _transacoes_grandes(db: DbSession, desde: dt.date) -> str | None:
    transacoes = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.data >= desde,
            func.abs(models.Transaction.valor) >= LARGE_TRANSACTION_THRESHOLD,
        )
        .all()
    )
    if not transacoes:
        return None
    linhas = "\n".join(
        f"- {t.descricao}: R$ {abs(t.valor):.2f} ({t.data.isoformat()})" for t in transacoes
    )
    return f"💸 Transações grandes (>= R$ {LARGE_TRANSACTION_THRESHOLD:.2f}):\n{linhas}"


def _gasto_incomum(db: DbSession, hoje: dt.date, ontem: dt.date) -> str | None:
    gasto_ontem = abs(
        db.query(func.coalesce(func.sum(models.Transaction.valor), 0))
        .filter(models.Transaction.tipo == "debit", models.Transaction.data == ontem)
        .scalar()
        or 0
    )
    if gasto_ontem <= 0:
        return None

    inicio_mes = hoje.replace(day=1)
    dias_com_dado = (ontem - inicio_mes).days  # dias completos antes de ontem
    if dias_com_dado <= 0:
        return None

    gasto_mes_ate_anteontem = abs(
        db.query(func.coalesce(func.sum(models.Transaction.valor), 0))
        .filter(
            models.Transaction.tipo == "debit",
            models.Transaction.data >= inicio_mes,
            models.Transaction.data < ontem,
        )
        .scalar()
        or 0
    )
    media_diaria = gasto_mes_ate_anteontem / dias_com_dado
    if media_diaria <= 0 or gasto_ontem < media_diaria * UNUSUAL_SPEND_MULTIPLIER:
        return None

    return (
        f"📈 Gasto de ontem ({ontem.isoformat()}) foi R$ {gasto_ontem:.2f}, "
        f"{UNUSUAL_SPEND_MULTIPLIER:.0f}x+ acima da média diária do mês "
        f"(R$ {media_diaria:.2f})."
    )
