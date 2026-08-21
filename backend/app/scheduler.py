"""Jobs em background da aplicação:

- **Dígest diário**: roda 1x/dia às 06:00, manda o email de resumo/alertas
  (`notifications.run_daily_digest`) com base nas transações já lançadas
  (manuais ou importadas de extrato). Também materializa parcelas vencidas
  antes de montar o dígest, pra "gasto do mês" já refletir a cobrança do
  dia (ver `services/parcelas.py`).
- **Lembrete de cobrança** (parcela de cartão + assinatura): véspera às
  20:00 (1x), e no próprio dia às 08:00 e 17:30 (2x) — só manda email se
  tiver algo cobrando na data (silencioso nos outros dias).
- **Lembrete de importar extrato**: 1x por semana (segunda 09:00), nudge
  genérico listando cada conta e há quanto tempo não recebe um import.
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
from .services import notifications, parcelas

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
        parcelas.materializar_parcelas_vencidas(db)
        notifications.run_daily_digest(db)
    finally:
        db.close()


def lembrete_cobranca_amanha() -> None:
    db = SessionLocal()
    try:
        notifications.lembrete_cobrancas(db, "amanha")
    finally:
        db.close()


def lembrete_cobranca_hoje() -> None:
    db = SessionLocal()
    try:
        parcelas.materializar_parcelas_vencidas(db)
        notifications.lembrete_cobrancas(db, "hoje")
    finally:
        db.close()


def lembrete_importar_extrato() -> None:
    db = SessionLocal()
    try:
        notifications.lembrete_importar_extrato(db)
    finally:
        db.close()


def materializar_parcelas_na_subida() -> None:
    """Roda uma vez quando a aplicação sobe — cobre o caso do servidor
    ter ficado fora do ar (deploy, free tier dormindo) durante a data de
    vencimento de alguma parcela, sem esperar o próximo dígest às 06:00."""
    db = SessionLocal()
    try:
        parcelas.materializar_parcelas_vencidas(db)
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
        lembrete_cobranca_amanha,
        "cron",
        hour=20,
        minute=0,
        id="lembrete_cobranca_amanha",
        replace_existing=True,
    )
    scheduler.add_job(
        lembrete_cobranca_hoje,
        "cron",
        hour=8,
        minute=0,
        id="lembrete_cobranca_manha",
        replace_existing=True,
    )
    scheduler.add_job(
        lembrete_cobranca_hoje,
        "cron",
        hour=17,
        minute=30,
        id="lembrete_cobranca_tarde",
        replace_existing=True,
    )
    scheduler.add_job(
        lembrete_importar_extrato,
        "cron",
        day_of_week="mon",
        hour=9,
        minute=0,
        id="lembrete_importar_extrato",
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
