import os

import httpx


def _api_url(method: str) -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    return f"https://api.telegram.org/bot{token}/{method}"


def enviar_mensagem(chat_id: int | str, texto: str) -> None:
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        return
    httpx.post(_api_url("sendMessage"), json={"chat_id": chat_id, "text": texto}, timeout=10)


def buscar_updates(offset: int | None = None, timeout: int = 25) -> list[dict]:
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    resp = httpx.get(_api_url("getUpdates"), params=params, timeout=timeout + 10)
    resp.raise_for_status()
    return resp.json().get("result", [])


def configurar_webhook(url_publica: str) -> dict:
    """Registra `{url_publica}/telegram/webhook` como webhook do bot,
    incluindo o `secret_token` (TELEGRAM_WEBHOOK_SECRET) — o Telegram
    manda esse valor de volta no header `X-Telegram-Bot-Api-Secret-Token`
    em toda chamada ao webhook, e `routers/telegram.py` confere que bate
    antes de processar qualquer coisa. Sem isso, qualquer um na internet
    poderia fazer POST no endpoint do webhook fingindo ser o Telegram.

    Rodar uma vez (ex: `python -c "from app.telegram_client import configurar_webhook;
    print(configurar_webhook('https://seu-backend.onrender.com'))"`) depois
    de definir TELEGRAM_BOT_TOKEN e TELEGRAM_WEBHOOK_SECRET no ambiente."""
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    if not secret:
        raise RuntimeError("TELEGRAM_WEBHOOK_SECRET não definido — gere um valor aleatório antes.")
    resp = httpx.post(
        _api_url("setWebhook"),
        json={"url": f"{url_publica.rstrip('/')}/telegram/webhook", "secret_token": secret},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
