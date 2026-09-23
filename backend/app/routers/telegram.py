import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..telegram_service import handle_update

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def webhook(
    request: Request,
    db: DbSession = Depends(get_db),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    # O Telegram manda de volta, em todo POST ao webhook, o mesmo
    # `secret_token` configurado no `setWebhook` (ver
    # `telegram_client.configurar_webhook`) — sem essa checagem, qualquer
    # um na internet poderia POSTar aqui fingindo ser o Telegram (a única
    # proteção seria adivinhar o `chat_id` dentro de `handle_update`, o
    # que não é uma barreira de autenticação de verdade).
    secret_esperado = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    if not secret_esperado or x_telegram_bot_api_secret_token != secret_esperado:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Webhook não autorizado")

    payload = await request.json()
    handle_update(db, payload)
    return {"ok": True}
