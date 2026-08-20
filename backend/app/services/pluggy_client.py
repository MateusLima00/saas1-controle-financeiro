"""Wrapper fino sobre a API da Pluggy (Conector 200 - sandbox).

Etapa 3 do passo-a-passo (`passo-a-passo-claude-code.md`): troca
PLUGGY_CLIENT_ID/PLUGGY_CLIENT_SECRET por uma API key de curta duração
(`POST /auth`), cacheada em memória e renovada só quando expira - esse é
o único segredo usado nas chamadas seguintes (`X-API-KEY`), nunca sai do
servidor.
"""
import datetime as dt
import os

import httpx

BASE_URL = "https://api.pluggy.ai"

_api_key: str | None = None
_api_key_expires_at: dt.datetime | None = None


class PluggyError(Exception):
    pass


def _client_credentials() -> tuple[str, str]:
    client_id = os.getenv("PLUGGY_CLIENT_ID")
    client_secret = os.getenv("PLUGGY_CLIENT_SECRET")
    if not (client_id and client_secret):
        raise PluggyError("PLUGGY_CLIENT_ID/PLUGGY_CLIENT_SECRET não configurados.")
    return client_id, client_secret


def get_api_key() -> str:
    """Retorna a API key cacheada, renovando se estiver expirada ou perto disso."""
    global _api_key, _api_key_expires_at

    if _api_key and _api_key_expires_at and dt.datetime.utcnow() < _api_key_expires_at:
        return _api_key

    client_id, client_secret = _client_credentials()
    resp = httpx.post(
        f"{BASE_URL}/auth",
        json={"clientId": client_id, "clientSecret": client_secret},
        timeout=30,
    )
    if resp.status_code != 200:
        raise PluggyError(f"Falha ao autenticar na Pluggy ({resp.status_code}): {resp.text}")

    data = resp.json()
    _api_key = data["apiKey"]
    # API key da Pluggy dura ~2h; renovamos 5 min antes de expirar por segurança.
    _api_key_expires_at = dt.datetime.utcnow() + dt.timedelta(hours=2, minutes=-5)
    return _api_key


def _headers() -> dict:
    return {"X-API-KEY": get_api_key()}


def _request(method: str, path: str, **kwargs) -> dict:
    resp = httpx.request(method, f"{BASE_URL}{path}", headers=_headers(), timeout=30, **kwargs)
    if resp.status_code >= 400:
        raise PluggyError(f"Pluggy {method} {path} falhou ({resp.status_code}): {resp.text}")
    # DELETE (e algumas respostas 204) voltam sem corpo — resp.json() daria
    # json.JSONDecodeError (não é um PluggyError, então quem chama não
    # conseguiria tratar isso de forma limpa).
    if not resp.content:
        return {}
    return resp.json()


def create_connect_token(item_id: str | None = None) -> str:
    """Gera um connect token de curta duração para o Pluggy Connect Widget
    (frontend). Se `item_id` for passado, o widget abre já em modo de
    atualização daquele item (re-login); senão abre pra conectar um banco
    novo (fluxo OAuth do Conector 200 - MeuPluggy)."""
    body = {"itemId": item_id} if item_id else {}
    data = _request("POST", "/connect_token", json=body)
    return data["accessToken"]


def get_item(item_id: str) -> dict:
    return _request("GET", f"/items/{item_id}")


def delete_item(item_id: str) -> None:
    """Desconecta o item na Pluggy (não afeta a conta bancária real, só a
    autorização de leitura). Chamado quando o usuário exclui, no nosso
    app, a última conta local vinculada a esse item."""
    _request("DELETE", f"/items/{item_id}")


def list_accounts(item_id: str) -> list[dict]:
    data = _request("GET", "/accounts", params={"itemId": item_id})
    return data.get("results", [])


def list_transactions(account_id: str, page_size: int = 500) -> list[dict]:
    resultados: list[dict] = []
    page = 1
    while True:
        data = _request(
            "GET",
            "/transactions",
            params={"accountId": account_id, "pageSize": page_size, "page": page},
        )
        resultados.extend(data.get("results", []))
        total_pages = data.get("totalPages", 1)
        if page >= total_pages:
            break
        page += 1
    return resultados
