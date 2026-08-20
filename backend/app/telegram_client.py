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
