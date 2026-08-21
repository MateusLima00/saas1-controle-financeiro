"""Regras de quando disparar email pro usuário. Cada checagem é
independente e nunca propaga exceção — notificação não pode derrubar o
sync nem nenhuma outra rota (ver `email_service.send_email`).

Gatilhos implementados:
- Meta atingida (chamado direto do router de goals, ao criar contribuição
  ou editar valor_atual).
- Resumo diário + saldo baixo/negativo + assinatura próxima de cobrar +
  transação grande + gasto incomum do dia — tudo junto num só email
  ("dígest diário"), rodado 1x/dia pelo scheduler (`run_daily_digest`).
- Lembretes de cobrança (parcela de cartão + assinatura): véspera (1x, à
  noite) e no próprio dia (2x — manhã e fim de tarde), rodados pelo
  scheduler (`lembrete_cobrancas`).
- Lembrete periódico de importar extrato (`lembrete_importar_extrato`).

Toda notificação também é espelhada pro Nero (POST em `NERO_NOTIFY_URL`,
se configurado), que manda a mesma mensagem por Telegram — canal
redundante ao email, pra não depender só de uma via.
"""
import datetime as dt
import logging
import os

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session as DbSession

from .. import models
from ..timezone_utils import hoje as _hoje
from .email_service import render_email_html, send_email

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


def _notificar_nero(mensagem: str) -> None:
    """Espelha a notificação pro Nero (canal Telegram), se configurado.
    Nunca levanta exceção — é sempre um canal extra, opcional."""
    url = os.getenv("NERO_NOTIFY_URL")
    token = os.getenv("NERO_INTEGRATION_TOKEN")
    if not (url and token):
        return
    try:
        httpx.post(
            url, json={"mensagem": mensagem}, headers={"Authorization": f"Bearer {token}"}, timeout=10
        )
    except Exception:
        logger.warning("Falha ao espelhar notificação pro Nero (não bloqueia o email).", exc_info=True)


def _enviar(assunto: str, corpo_texto: str, html: str) -> None:
    send_email(assunto, corpo_texto, html=html)
    _notificar_nero(f"{assunto}\n\n{corpo_texto}")


def notify_goal_achieved(goal: "models.Goal") -> None:
    corpo = f'Sua meta "{goal.nome}" bateu o valor alvo! Valor atual: R$ {goal.valor_atual:.2f} / Valor alvo: R$ {goal.valor_alvo:.2f}'
    html = render_email_html(
        titulo=f'Meta atingida: {goal.nome}',
        subtitulo="Parabéns! Você bateu o valor alvo dessa meta.",
        itens=[(goal.nome, f"R$ {goal.valor_atual:.2f} de R$ {goal.valor_alvo:.2f}")],
        tipo="sucesso",
    )
    _enviar(f"🎉 Meta atingida: {goal.nome}", corpo, html)


def run_daily_digest(db: DbSession) -> None:
    try:
        hoje = _hoje()
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
        html = render_email_html(
            titulo="Resumo financeiro",
            subtitulo=hoje.strftime("%d/%m/%Y"),
            itens=[(linha.split("\n")[0], "") for linha in partes],
            tipo="info",
            rodape="Dígest diário — enviado todo dia às 06:00.",
        )
        _enviar(f"📊 Resumo financeiro — {hoje.strftime('%d/%m/%Y')}", corpo, html)
    except Exception:
        logger.exception("Falha ao montar o dígest diário de notificações.")


def _resumo(db: DbSession) -> str:
    saldo_total = db.query(func.coalesce(func.sum(models.Account.saldo), 0)).scalar() or 0
    hoje = _hoje()
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


def _proxima_cobranca_como_data(proxima_cobranca: str | None, hoje: dt.date) -> dt.date | None:
    """`proxima_cobranca` é salvo como texto "DD/MM" (sem ano, ver
    Assinaturas.jsx) — pra comparar com uma data de verdade, assume o ano
    atual, ou o próximo ano se esse dia/mês já passou (assinatura anual
    tipo "18/09" cobrando de novo no ano seguinte)."""
    if not proxima_cobranca:
        return None
    try:
        dia, mes = (int(p) for p in proxima_cobranca.split("/")[:2])
        data = dt.date(hoje.year, mes, dia)
        if data < hoje:
            data = dt.date(hoje.year + 1, mes, dia)
        return data
    except (ValueError, IndexError):
        return None


def _assinaturas_no_periodo(db: DbSession, inicio: dt.date, fim: dt.date) -> list[tuple["models.Subscription", dt.date]]:
    resultado = []
    for assinatura in db.query(models.Subscription).all():
        data = _proxima_cobranca_como_data(assinatura.proxima_cobranca, inicio)
        if data and inicio <= data <= fim:
            resultado.append((assinatura, data))
    return resultado


def _assinaturas_proximas(db: DbSession, hoje: dt.date) -> str | None:
    limite = hoje + dt.timedelta(days=SUBSCRIPTION_ALERT_DAYS)
    assinaturas = _assinaturas_no_periodo(db, hoje, limite)
    if not assinaturas:
        return None
    linhas = "\n".join(
        f"- {a.nome}: R$ {a.valor:.2f} em {a.proxima_cobranca}" for a, _ in assinaturas
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


def _cobrancas_do_dia(db: DbSession, data_alvo: dt.date) -> list[tuple[str, str]]:
    """Parcelas de compra parcelada + assinaturas com cobrança em
    `data_alvo` — formato pronto pro template de email (linha principal,
    linha secundária)."""
    itens = []

    parcelas = (
        db.query(models.Parcela)
        .join(models.CompraParcelada, models.Parcela.compra_id == models.CompraParcelada.id)
        .filter(models.Parcela.data_vencimento == data_alvo)
        .all()
    )
    for parcela in parcelas:
        compra = parcela.compra
        itens.append(
            (
                f"💳 {compra.descricao} ({parcela.numero}/{compra.num_parcelas})",
                f"R$ {parcela.valor:.2f} · {compra.conta.banco if compra.conta else 'cartão'}",
            )
        )

    for assinatura, data in _assinaturas_no_periodo(db, data_alvo, data_alvo):
        itens.append((f"🔁 {assinatura.nome}", f"R$ {assinatura.valor:.2f} · assinatura {assinatura.ciclo.lower()}"))

    return itens


def lembrete_cobrancas(db: DbSession, quando: str) -> None:
    """`quando`: "amanha" (roda 1x, à noite da véspera) ou "hoje" (roda 2x
    no próprio dia — manhã e fim de tarde). Só manda email se tiver algo
    de fato cobrando na data — silencioso nos dias sem nada agendado."""
    try:
        hoje = _hoje()
        data_alvo = hoje + dt.timedelta(days=1) if quando == "amanha" else hoje
        itens = _cobrancas_do_dia(db, data_alvo)
        if not itens:
            return

        quando_texto = "amanhã" if quando == "amanha" else "hoje"
        titulo = f"Cobrança prevista para {quando_texto}"
        subtitulo = data_alvo.strftime("%d/%m/%Y")
        corpo_texto = "\n".join(f"- {principal}: {secundaria}" for principal, secundaria in itens)
        html = render_email_html(
            titulo=titulo, subtitulo=subtitulo, itens=itens, tipo="aviso",
            rodape="Lembrete automático — véspera à noite e 2x no dia da cobrança.",
        )
        _enviar(f"📅 {titulo} ({subtitulo})", corpo_texto, html)
    except Exception:
        logger.exception("Falha ao montar o lembrete de cobrança (%s).", quando)


def lembrete_importar_extrato(db: DbSession) -> None:
    """Nudge periódico pra não deixar o extrato desatualizado — lista cada
    conta e há quanto tempo não recebe um import."""
    try:
        contas = db.query(models.Account).all()
        if not contas:
            return
        hoje = _hoje()
        itens = []
        for conta in contas:
            if conta.ultima_sync and conta.ultima_sync != "manual":
                try:
                    dias = (hoje - dt.date.fromisoformat(conta.ultima_sync)).days
                    detalhe = f"último import há {dias} dia(s)" if dias > 0 else "importado hoje"
                except ValueError:
                    detalhe = conta.ultima_sync
            else:
                detalhe = "nunca importado"
            itens.append((conta.banco, detalhe))

        html = render_email_html(
            titulo="Hora de atualizar o extrato",
            subtitulo="Baixe o extrato do banco e importe pra manter os dados em dia.",
            itens=itens,
            tipo="info",
            rodape="Lembrete periódico — importe pela tela Contas (CSV, OFX ou PDF).",
        )
        corpo_texto = "\n".join(f"- {banco}: {detalhe}" for banco, detalhe in itens)
        _enviar("🗂️ Hora de atualizar o extrato", corpo_texto, html)
    except Exception:
        logger.exception("Falha ao montar o lembrete de importar extrato.")
