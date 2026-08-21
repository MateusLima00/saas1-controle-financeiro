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


def trigger_item_update(item_id: str) -> dict:
    """Manda a Pluggy buscar dado novo na fonte (banco/MeuPluggy) pro
    item, em vez de só ler o que já está em cache do lado da Pluggy.

    Sem isso, `list_accounts`/`list_transactions` só devolvem o último
    snapshot que a Pluggy já tinha — que só fica novo quando ALGUÉM
    força um refresh (ex: o usuário clicando "atualizar" manualmente no
    meu.pluggy.ai, no caso do Conector 200/MeuPluggy, que é uma ponte
    pra lá). `PATCH /items/{id}` é o mesmo request que o próprio Pluggy
    Connect Widget dispara ao reconectar/atualizar um item."""
    return _request("PATCH", f"/items/{item_id}", json={})


def delete_item(item_id: str) -> None:
    """Desconecta o item na Pluggy (não afeta a conta bancária real, só a
    autorização de leitura). Chamado quando o usuário exclui, no nosso
    app, a última conta local vinculada a esse item."""
    _request("DELETE", f"/items/{item_id}")


def list_accounts(item_id: str) -> list[dict]:
    data = _request("GET", "/accounts", params={"itemId": item_id})
    return data.get("results", [])


def list_transactions(account_id: str) -> list[dict]:
    """Busca todas as transações de uma conta, paginando até o fim.

    Pede explicitamente `createdAtFrom` = 12 meses atrás: sem esse
    parâmetro a Pluggy aplica um período padrão mais curto. 12 meses é o
    teto que o Open Finance normalmente autoriza pra maioria dos
    bancos/conectores (histórico mais antigo que isso costuma não estar
    disponível nem do lado do banco, independente do que a gente pedir
    aqui).

    `GET /transactions` (paginação por `page`/`totalPages`) foi
    descontinuado pela Pluggy (410 ENDPOINT_DEPRECATED) — o substituto
    `GET /v2/transactions` **não aceita `pageSize`/`page`/`cursor`/`from`
    nenhum** (validado empiricamente contra a API: qualquer um desses
    dá 400 "property X should not exist"). Os únicos query params
    aceitos são `accountId` e `createdAtFrom`; a paginação é via campo
    `next` na resposta — uma URL completa e pronta pra chamar (ou
    `null` quando acabou), não um token/cursor pra montar você mesmo."""
    desde = (dt.date.today() - dt.timedelta(days=365)).isoformat()

    resultados: list[dict] = []
    data = _request(
        "GET", "/v2/transactions", params={"accountId": account_id, "createdAtFrom": desde}
    )
    resultados.extend(data.get("results", []))
    next_url = data.get("next")
    while next_url:
        resp = httpx.get(next_url, headers=_headers(), timeout=30)
        if resp.status_code >= 400:
            raise PluggyError(f"Pluggy GET {next_url} falhou ({resp.status_code}): {resp.text}")
        data = resp.json()
        resultados.extend(data.get("results", []))
        next_url = data.get("next")
    return resultados
