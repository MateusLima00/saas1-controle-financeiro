"""Jobs em background da aplicação:

- **Dígest diário**: roda 1x/dia às 06:00, manda o email de resumo/alertas
  (`notifications.run_daily_digest`) com base nas transações já lançadas
  (manuais ou importadas de extrato).
- **Keep-alive** (Etapa 3.5 / hospedagem): faz um GET periódico na própria
  URL pública do app, pra evitar que o free tier do Render "durma" após
  15 min sem tráfego. Só roda se `SELF_PING_URL` estiver configurada
  (inútil em dev local); em produção, aponta pra própria URL do Render
  (ex: `SELF_PING_URL=https://saas1-backend.onrender.com`).
"""
import logging
import os

import httpx
from apscheduler.schedulers.background import BackgroundScheduler

from .database import SessionLocal
from .services import notifications

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


def run_daily_digest() -> None:
    db = SessionLocal()
    try:
        notifications.run_daily_digest(db)
    finally:
        db.close()


def start():
    if scheduler.running:
        return
    scheduler.add_job(
        run_daily_digest,
        "cron",
        hour=6,
        minute=0,
        id="daily_digest",
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
