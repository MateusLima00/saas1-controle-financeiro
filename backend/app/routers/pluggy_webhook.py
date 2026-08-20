"""Webhook da Pluggy — exigido pra liberar acesso a dados reais (produção)
no dashboard.pluggy.ai (fluxo "Solicitar Acesso à Produção" → "Registre
webhooks pra eventos-chave"). Sem auth de sessão (é a Pluggy chamando,
não o navegador do usuário) — a Pluggy não assina esses webhooks com
segredo compartilhado no plano atual, então tratamos como um sinal pra
disparar sync, não como fonte de verdade sensível (o pior caso de alguém
forjar uma chamada aqui é um sync a mais, não vazamento/alteração de
dado nenhum).

Responde rápido (a Pluggy exige 2XX em até 5s) e faz o sync de verdade
em background."""
import logging

from fastapi import APIRouter, BackgroundTasks, Request

from ..database import SessionLocal
from ..services import notifications, pluggy_client, pluggy_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pluggy", tags=["pluggy"])

_EVENTOS_DE_SYNC = {
    "item/created",
    "item/updated",
    "transactions/created",
    "transactions/updated",
    "transactions/deleted",
    "all",
}


@router.post("/webhook")
async def pluggy_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    evento = payload.get("event", "")
    item_id = payload.get("itemId")

    if evento in _EVENTOS_DE_SYNC and item_id:
        background_tasks.add_task(_sync_em_background, item_id)
    elif evento == "item/error" and item_id:
        erro = payload.get("error", {})
        background_tasks.add_task(notifications.notify_sync_failure, item_id, str(erro))

    return {"received": True}


def _sync_em_background(item_id: str) -> None:
    db = SessionLocal()
    try:
        contas = pluggy_sync.sync_item(db, item_id)
        db.commit()
        logger.info("Webhook da Pluggy: item %s sincronizado (%d conta(s)).", item_id, contas)
    except pluggy_client.PluggyError as exc:
        db.rollback()
        logger.error("Webhook da Pluggy: falha ao sincronizar item %s: %s", item_id, exc)
    finally:
        db.close()
