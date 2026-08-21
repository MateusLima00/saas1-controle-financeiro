"""Serviço isolado só pra automatizar o "Atualizar" do meu.pluggy.ai.

Fica separado do backend principal do Saas1 de propósito: a senha de app
do Gmail (usada pra ler o link de login) nunca fica visível/acessível pro
backend principal (que lida com sessão de usuário, dados financeiros,
integração do Nero). Se esse serviço aqui tiver algum problema de
segurança, o pior caso é vazar acesso à automação de refresh — não ao
Gmail nem ao dado financeiro em si (esse continua só no backend
principal).

Uma rota só: POST /atualizar, protegida por Bearer token
(REFRESH_TOKEN). Roda a automação em background (BackgroundTasks) e
responde 202 na hora — o caller não fica esperando os ~1-2 min que o
fluxo inteiro leva. No final, chama de volta o backend principal pra
sincronizar os dados frescos."""
import logging
import os

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException

from atualizar import rodar_atualizacao_completa

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="meupluggy-refresher")

REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]
MEU_PLUGGY_EMAIL = os.environ["MEU_PLUGGY_EMAIL"]
IMAP_EMAIL = os.environ.get("MEU_PLUGGY_IMAP_EMAIL", MEU_PLUGGY_EMAIL)
IMAP_APP_PASSWORD = os.environ["MEU_PLUGGY_IMAP_APP_PASSWORD"]

SAAS1_API_URL = os.environ.get("SAAS1_API_URL", "")
SAAS1_CALLBACK_TOKEN = os.environ.get("SAAS1_CALLBACK_TOKEN", "")

_em_andamento = False


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/atualizar", status_code=202)
def atualizar(background_tasks: BackgroundTasks, authorization: str = Header(default="")):
    if authorization != f"Bearer {REFRESH_TOKEN}":
        raise HTTPException(401, "Token inválido.")

    global _em_andamento
    if _em_andamento:
        return {"status": "ja_em_andamento"}

    background_tasks.add_task(_executar)
    return {"status": "iniciado"}


def _executar() -> None:
    global _em_andamento
    _em_andamento = True
    try:
        resultado = rodar_atualizacao_completa(MEU_PLUGGY_EMAIL, IMAP_EMAIL, IMAP_APP_PASSWORD)
        logger.info("Atualização concluída: %s", resultado)
        _chamar_callback_do_saas1()
    except Exception:
        logger.exception("Falha ao rodar a atualização do meu.pluggy.ai.")
    finally:
        _em_andamento = False


def _chamar_callback_do_saas1() -> None:
    if not (SAAS1_API_URL and SAAS1_CALLBACK_TOKEN):
        logger.info("SAAS1_API_URL/SAAS1_CALLBACK_TOKEN não configurados, pulando callback.")
        return
    try:
        resp = httpx.post(
            f"{SAAS1_API_URL.rstrip('/')}/integrations/meupluggy-refresh-callback",
            headers={"Authorization": f"Bearer {SAAS1_CALLBACK_TOKEN}"},
            timeout=30,
        )
        logger.info("Callback pro Saas1: %s", resp.status_code)
    except Exception:
        logger.exception("Falha ao chamar o callback do Saas1 (dado ainda vai ser pego pelo job de 20min).")
