"""Lógica de upsert de contas/transações a partir da Pluggy — reaproveitada
tanto pelo endpoint `POST /accounts/sync` (botão "atualizar agora") quanto
pelo job diário automático (`app/scheduler.py`)."""
import datetime as dt

from sqlalchemy.orm import Session as DbSession

from .. import models
from ..categorization import categoria_para_descricao
from . import pluggy_client

_PLUGGY_SUBTYPE_PARA_TIPO = {
    "CHECKING_ACCOUNT": "checking",
    "SAVINGS_ACCOUNT": "savings",
    "CREDIT_CARD": "credit_card",
}


def sync_item(db: DbSession, item_id: str) -> int:
    """Sincroniza todas as contas de um item da Pluggy. Retorna quantas
    contas foram atualizadas. Não faz commit — quem chama decide quando."""
    contas_pluggy = pluggy_client.list_accounts(item_id)

    contas_atualizadas = 0
    for conta_pluggy in contas_pluggy:
        account = _upsert_account(db, item_id, conta_pluggy)
        _sincronizar_transacoes(db, account)
        contas_atualizadas += 1

    return contas_atualizadas


def distinct_item_ids(db: DbSession) -> list[str]:
    linhas = (
        db.query(models.Account.pluggy_item_id)
        .filter(models.Account.pluggy_item_id.isnot(None))
        .distinct()
        .all()
    )
    return [item_id for (item_id,) in linhas]


def _upsert_account(db: DbSession, item_id: str, conta_pluggy: dict) -> models.Account:
    pluggy_account_id = conta_pluggy["id"]
    account = (
        db.query(models.Account)
        .filter(models.Account.pluggy_account_id == pluggy_account_id)
        .first()
    )
    if not account:
        account = models.Account(pluggy_account_id=pluggy_account_id, origem="pluggy")
        db.add(account)

    subtype = conta_pluggy.get("subtype") or ""
    account.banco = conta_pluggy.get("name") or account.banco or "Conta Pluggy"
    account.tipo = _PLUGGY_SUBTYPE_PARA_TIPO.get(subtype, "checking")
    account.saldo = conta_pluggy.get("balance") or 0
    account.status = "connected"
    account.ultima_sync = dt.date.today().isoformat()
    account.pluggy_item_id = item_id
    db.flush()
    return account


def _sincronizar_transacoes(db: DbSession, account: models.Account) -> None:
    transacoes = pluggy_client.list_transactions(account.pluggy_account_id)
    for t in transacoes:
        external_id = f"pluggy:{t['id']}"
        existente = (
            db.query(models.Transaction)
            .filter(models.Transaction.external_id == external_id)
            .first()
        )
        if existente:
            continue

        descricao = t.get("description") or "Sem descrição"
        categoria = categoria_para_descricao(db, descricao)
        db.add(
            models.Transaction(
                data=dt.date.fromisoformat(t["date"][:10]),
                descricao=descricao,
                valor=abs(t.get("amount") or 0),
                tipo=(t.get("type") or "DEBIT").lower(),
                categoria_id=categoria.id if categoria else None,
                conta_id=account.id,
                origem="pluggy",
                external_id=external_id,
            )
        )
