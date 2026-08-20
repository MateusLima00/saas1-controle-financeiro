"""Jobs em background da aplicação:

- **Sync frequente da Pluggy**: roda a cada 20 min, sincronizando todo
  item já conectado (`Account.pluggy_item_id`). Roda sempre, mesmo sem
  ninguém com o app aberto — o uso principal é via bot do Telegram
  (Nero), não pela tela do navegador, então não dá pra depender de um
  timer no frontend. Silencioso: só loga, não manda email de erro toda
  hora (isso ficaria muito repetitivo se um banco cair).
- **Dígest diário**: roda 1x/dia às 06:00, faz o mesmo sync e, além
  disso, manda o email de resumo/alertas (`notifications.run_daily_digest`)
  e notifica falha por email (só aqui, 1x/dia, pra não spammar).
- **Keep-alive** (Etapa 3.5 / hospedagem): faz um GET periódico na própria
  URL pública do app, pra evitar que o free tier do Render "durma" após
  15 min sem tráfego. Só roda se `SELF_PING_URL` estiver configurada
  (inútil em dev local); em produção, aponta pra própria URL do Render
  (ex: `SELF_PING_URL=https://saas1-backend.onrender.com`).

Contas sem nenhum item conectado ainda não são afetadas por nenhum desses
jobs — conectar um banco continua exigindo o Pluggy Connect Widget (ação
do usuário, uma vez).
"""
import logging
import os

import httpx
from apscheduler.schedulers.background import BackgroundScheduler

from .database import SessionLocal
from .services import notifications, pluggy_client, pluggy_sync

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")


def keep_alive_ping() -> None:
    url = os.getenv("SELF_PING_URL")
    if not url:
        return
    try:
        resp = httpx.get(f"{url.rstrip('/')}/health", timeout=10)
        logger.info("Keep-alive ping: %s -> %s", url, resp.status_code)
    except Exception as exc:
        logger.warning("Keep-alive ping falhou: %s", exc)


def _sync_all_items(db, *, log_prefix: str) -> dict[str, Exception | None]:
    """Sincroniza todo item conectado. Retorna {item_id: erro_ou_None}.
    Não notifica nada — quem chama decide o que fazer com falhas."""
    resultados: dict[str, Exception | None] = {}
    item_ids = pluggy_sync.distinct_item_ids(db)
    if not item_ids:
        logger.info("%s: nenhum item conectado ainda.", log_prefix)
        return resultados

    for item_id in item_ids:
        try:
            contas = pluggy_sync.sync_item(db, item_id)
            db.commit()
            logger.info("%s: item %s ok (%d conta(s)).", log_prefix, item_id, contas)
            resultados[item_id] = None
        except pluggy_client.PluggyError as exc:
            db.rollback()
            logger.error("%s: falhou pro item %s: %s", log_prefix, item_id, exc)
            resultados[item_id] = exc

    return resultados


def run_frequent_sync() -> None:
    """Roda a cada 20 min — sync silencioso, sem email (evita spam se um
    banco ficar fora do ar por horas: o email de falha só sai 1x/dia, no
    dígest)."""
    if not (os.getenv("PLUGGY_CLIENT_ID") and os.getenv("PLUGGY_CLIENT_SECRET")):
        return
    db = SessionLocal()
    try:
        _sync_all_items(db, log_prefix="Sync frequente da Pluggy")
    finally:
        db.close()


def run_daily_sync() -> None:
    if not (os.getenv("PLUGGY_CLIENT_ID") and os.getenv("PLUGGY_CLIENT_SECRET")):
        logger.info("Sync diário da Pluggy ignorado: credenciais não configuradas.")
        return

    db = SessionLocal()
    try:
        resultados = _sync_all_items(db, log_prefix="Sync diário da Pluggy")
        for item_id, erro in resultados.items():
            if erro is not None:
                notifications.notify_sync_failure(item_id, str(erro))

        notifications.run_daily_digest(db)
    finally:
        db.close()


def start():
    if scheduler.running:
        return
    scheduler.add_job(
        run_frequent_sync,
        "interval",
        minutes=20,
        id="pluggy_frequent_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        run_daily_sync,
        "cron",
        hour=6,
        minute=0,
        id="pluggy_daily_sync",
        replace_existing=True,
    )
    scheduler.add_job(
        keep_alive_ping,
        "interval",
        minutes=8,
        id="keep_alive_ping",
        replace_existing=True,
    )
    scheduler.start()


def stop():
    if scheduler.running:
        scheduler.shutdown(wait=False)
