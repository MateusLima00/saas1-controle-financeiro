"""Lógica de upsert de contas/transações a partir da Pluggy — reaproveitada
tanto pelo endpoint `POST /accounts/sync` (botão "atualizar agora") quanto
pelo job diário automático (`app/scheduler.py`)."""
import datetime as dt

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from .. import models
from ..categorization import categoria_para_descricao
from ..timezone_utils import hoje
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


def sync_all_items(db: DbSession) -> dict[str, Exception | None]:
    """Sincroniza TODOS os itens já conectados (todos os bancos, não só
    um). Usada tanto pelo botão "Atualizar agora" (sem itemId no corpo)
    quanto pelos jobs em background (`app/scheduler.py`) — sem isso, uma
    conta com vários bancos conectados só teria o primeiro item
    atualizado a cada sync. Cada item é commitado (ou revertido)
    independentemente, então a falha de um banco não afeta os outros.
    Retorna {item_id: erro_ou_None}."""
    resultados: dict[str, Exception | None] = {}
    for item_id in distinct_item_ids(db):
        try:
            sync_item(db, item_id)
            db.commit()
            resultados[item_id] = None
        except pluggy_client.PluggyError as exc:
            db.rollback()
            resultados[item_id] = exc
    return resultados


def _preencher_campos(account: models.Account, item_id: str, conta_pluggy: dict) -> None:
    subtype = conta_pluggy.get("subtype") or ""
    account.banco = conta_pluggy.get("name") or account.banco or "Conta Pluggy"
    account.tipo = _PLUGGY_SUBTYPE_PARA_TIPO.get(subtype, "checking")
    account.saldo = conta_pluggy.get("balance") or 0
    account.status = "connected"
    account.ultima_sync = hoje().isoformat()
    account.pluggy_item_id = item_id


def _upsert_account(db: DbSession, item_id: str, conta_pluggy: dict) -> models.Account:
    pluggy_account_id = conta_pluggy["id"]
    account = (
        db.query(models.Account)
        .filter(models.Account.pluggy_account_id == pluggy_account_id)
        .first()
    )
    if account:
        _preencher_campos(account, item_id, conta_pluggy)
        db.flush()
        return account

    # Conta nova: preenche os campos (inclusive os NOT NULL) ANTES de
    # flushar — flushar um objeto "vazio" e só depois setar os campos
    # dá NotNullViolation. O insert em si vai num savepoint (begin_nested)
    # pra isolar uma eventual corrida (outra chamada concorrente criando a
    # mesma conta entre nosso SELECT e o INSERT) sem derrubar as outras
    # contas já sincronizadas nesta mesma transação.
    account = models.Account(pluggy_account_id=pluggy_account_id, origem="pluggy")
    _preencher_campos(account, item_id, conta_pluggy)
    db.add(account)
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError:
        # Expunge é essencial aqui: sem isso o autoflush do próximo
        # db.query(...) tentaria flushar esse mesmo objeto quebrado de
        # novo, fora de qualquer savepoint, corrompendo a transação
        # inteira (PendingRollbackError daí pra frente).
        db.expunge(account)
        account = (
            db.query(models.Account)
            .filter(models.Account.pluggy_account_id == pluggy_account_id)
            .first()
        )
        _preencher_campos(account, item_id, conta_pluggy)
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
