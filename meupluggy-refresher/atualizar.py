"""Lógica de automação em si — login passwordless no meu.pluggy.ai (link
mágico por email, lido via IMAP) e clique em "Atualizar" em cada conexão
bancária. Reaproveitado pelo endpoint HTTP em `main.py`.

Ver README.md deste serviço pra explicação completa de por que isso existe
isolado (não faz parte do backend principal do Saas1)."""
from __future__ import annotations

import datetime as dt
import email
import imaplib
import logging
import re
import time

from playwright.sync_api import Page, sync_playwright

logger = logging.getLogger(__name__)

LOGIN_TIMEOUT_SEGUNDOS = 90
ATUALIZACAO_TIMEOUT_SEGUNDOS = 60


def _corpo_texto(msg: email.message.Message) -> str:
    if msg.is_multipart():
        partes = []
        for parte in msg.walk():
            if parte.get_content_type() in ("text/plain", "text/html"):
                try:
                    partes.append(parte.get_payload(decode=True).decode(errors="ignore"))
                except Exception:
                    pass
        return "\n".join(partes)
    payload = msg.get_payload(decode=True)
    return payload.decode(errors="ignore") if payload else ""


def _extrair_link_de_login(corpo: str) -> str | None:
    match = re.search(r'https://my-pluggy\.us\.auth0\.com/\S+', corpo)
    if not match:
        return None
    return match.group(0).rstrip('"\'<>)')


def buscar_link_de_login(imap_email: str, imap_senha_app: str) -> str:
    prazo = time.time() + LOGIN_TIMEOUT_SEGUNDOS
    logger.info("Esperando o email de login chegar em %s...", imap_email)
    while time.time() < prazo:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        try:
            imap.login(imap_email, imap_senha_app)
            imap.select("INBOX")
            hoje_imap = dt.datetime.now().strftime("%d-%b-%Y")
            _, dados = imap.search(None, f'SINCE {hoje_imap} FROM "pluggy.ai"')
            ids = dados[0].split()
            for msg_id in reversed(ids):
                _, msg_dados = imap.fetch(msg_id, "(RFC822)")
                msg = email.message_from_bytes(msg_dados[0][1])
                link = _extrair_link_de_login(_corpo_texto(msg))
                if link:
                    imap.store(msg_id, "+FLAGS", "\\Seen")
                    return link
        finally:
            imap.logout()
        time.sleep(4)
    raise TimeoutError("Não recebeu o email de login a tempo (confira a caixa de entrada manualmente).")


def _clicar_resiliente(page: Page, texto: str, timeout_ms: int = 15000) -> None:
    """`page.click()` puro às vezes trava esperando a ação "completar" quando
    tem uma animação/overlay (ex: cookie banner) por cima no instante do
    clique — nesse site isso já aconteceu no botão "Entrar". Tenta um clique
    normal primeiro; se travar, cai pra `force=True` (ignora a checagem de
    "estável"/sobreposição, só garante que o elemento existe)."""
    locator = page.get_by_text(texto, exact=True).first
    try:
        locator.click(timeout=timeout_ms)
    except Exception:
        logger.warning('Clique normal em "%s" travou, tentando force=True.', texto)
        locator.click(timeout=timeout_ms, force=True)


def logar(page: Page, meu_pluggy_email: str, imap_email: str, imap_senha_app: str) -> None:
    page.goto("https://meu.pluggy.ai/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)
    _clicar_resiliente(page, "Entrar")
    page.wait_for_selector('input[type="email"]', timeout=15000)
    page.fill('input[type="email"]', meu_pluggy_email)
    _clicar_resiliente(page, "Enviar")
    page.wait_for_timeout(1500)

    link = buscar_link_de_login(imap_email, imap_senha_app)
    logger.info("Link de login encontrado, autenticando...")
    page.goto(link, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)


def listar_links_de_conexoes(page: Page) -> list[str]:
    page.goto("https://meu.pluggy.ai/connections", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)
    hrefs = {
        a.get_attribute("href")
        for a in page.query_selector_all('a[href^="/connections/"]')
        if a.get_attribute("href") and a.get_attribute("href") != "/connections"
    }
    if not hrefs:
        # Diagnóstico: sem isso, um "0 conexões" fica impossível de
        # investigar remotamente (não temos acesso a screenshot deste
        # container). Loga onde a navegação realmente parou.
        logger.warning(
            "Nenhuma conexão encontrada — page.url=%s, title=%s", page.url, page.title()
        )
    return sorted(hrefs)


def atualizar_conexao(page: Page, href: str) -> bool:
    url = f"https://meu.pluggy.ai{href}"
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)
    try:
        _clicar_resiliente(page, "Atualizar", timeout_ms=15000)
    except Exception as exc:
        logger.warning("%s: não consegui clicar em Atualizar (%s)", url, exc)
        return False

    try:
        page.wait_for_selector(
            "text=Atualizando a sua conta", state="hidden", timeout=ATUALIZACAO_TIMEOUT_SEGUNDOS * 1000
        )
    except Exception:
        logger.warning("%s: atualização demorou mais que %ss, seguindo.", url, ATUALIZACAO_TIMEOUT_SEGUNDOS)
    return True


def rodar_atualizacao_completa(meu_pluggy_email: str, imap_email: str, imap_senha_app: str) -> dict:
    """Faz login e atualiza todas as conexões. Retorna um resumo (pra log/callback)."""
    resultado = {"conexoes_encontradas": 0, "atualizadas": 0, "falhas": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            logar(page, meu_pluggy_email, imap_email, imap_senha_app)

            links = listar_links_de_conexoes(page)
            resultado["conexoes_encontradas"] = len(links)
            logger.info("%d conexão(ões) encontrada(s).", len(links))

            for href in links:
                ok = atualizar_conexao(page, href)
                if ok:
                    resultado["atualizadas"] += 1
                else:
                    resultado["falhas"].append(href)
        finally:
            browser.close()

    return resultado
