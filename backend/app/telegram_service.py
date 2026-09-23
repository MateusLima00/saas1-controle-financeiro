import datetime as dt
import os

from sqlalchemy.orm import Session as DbSession

from . import models
from .auth import get_owner_user_id
from .categorization import categoria_para_descricao
from .message_parser import MensagemInvalida, parse_mensagem
from .routers.dashboard import _gasto_no_mes
from .telegram_client import enviar_mensagem


def _formatar_real(valor: float) -> str:
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "#").replace(".", ",").replace("#", ".")


def _chat_autorizado(chat_id: int | str) -> bool:
    esperado = os.getenv("TELEGRAM_CHAT_ID", "")
    return esperado != "" and str(chat_id) == str(esperado)


def _resumo_texto(db: DbSession, owner_id: int) -> str:
    from sqlalchemy import func

    hoje = dt.date.today()
    saldo_total = (
        db.query(func.coalesce(func.sum(models.Account.saldo), 0))
        .filter(models.Account.user_id == owner_id)
        .scalar()
        or 0
    )
    gasto_mes = _gasto_no_mes(db, owner_id, hoje.year, hoje.month)
    return (
        f"Saldo total: {_formatar_real(saldo_total)}\n"
        f"Gasto em {hoje.strftime('%m/%Y')}: {_formatar_real(gasto_mes)}"
    )


def handle_update(db: DbSession, update: dict) -> None:
    mensagem = update.get("message") or update.get("edited_message")
    if not mensagem:
        return

    chat_id = mensagem.get("chat", {}).get("id")
    texto = (mensagem.get("text") or "").strip()
    if not texto or chat_id is None:
        return

    if not _chat_autorizado(chat_id):
        return

    owner_id = get_owner_user_id(db)
    if owner_id is None:
        enviar_mensagem(chat_id, "Nenhum usuário cadastrado ainda no Saas1.")
        return

    if texto.lower().startswith("/resumo"):
        enviar_mensagem(chat_id, _resumo_texto(db, owner_id))
        return

    if texto.startswith("/"):
        enviar_mensagem(chat_id, "Comandos disponíveis: /resumo")
        return

    try:
        parsed = parse_mensagem(texto)
    except MensagemInvalida as exc:
        enviar_mensagem(chat_id, str(exc))
        return

    categoria = categoria_para_descricao(db, parsed.descricao, owner_id) if owner_id else None
    transacao = models.Transaction(
        data=parsed.data,
        descricao=parsed.descricao,
        valor=parsed.valor if parsed.tipo == "credit" else -parsed.valor,
        tipo=parsed.tipo,
        categoria_id=categoria.id if categoria else None,
        origem="telegram",
        user_id=owner_id,
    )
    db.add(transacao)
    db.commit()

    saldo_total = db.query(models.Account.saldo).filter(models.Account.user_id == owner_id).all()
    saldo_total = sum(s[0] for s in saldo_total)

    resposta = (
        f"Lançamento registrado: {_formatar_real(parsed.valor)} — {parsed.descricao}"
        f"\nCategoria: {categoria.nome if categoria else 'sem categoria'}"
        f"\nSaldo total: {_formatar_real(saldo_total)}"
    )
    enviar_mensagem(chat_id, resposta)
