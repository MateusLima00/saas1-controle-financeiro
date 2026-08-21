"""Script standalone (não faz parte da API) que automatiza o "atualizar" que
hoje é feito manualmente no site meu.pluggy.ai: login (passwordless, via
link mágico por e-mail), clica em "Atualizar" em cada banco conectado, e no
fim já dispara a sincronização do nosso próprio backend (`pluggy_sync`) pra
puxar os dados frescos pro nosso banco na hora, sem esperar o job de 20 min.

Por quê isso existe: o conector "MeuPluggy" que usamos pra conectar os
bancos (Etapa 3 do passo-a-passo) é uma ponte pro meu.pluggy.ai — nosso
próprio sync (`PATCH /items/{id}`) não força ELE a buscar dado novo no
banco, só re-lê o que já tiver disponível. Quem decide quando os dados
ficam frescos é o próprio meu.pluggy.ai. Esse script automatiza o passo
manual que faltava.

Credenciais (NUNCA commitar, sempre via variável de ambiente):
  MEU_PLUGGY_EMAIL             email de login no meu.pluggy.ai
  MEU_PLUGGY_IMAP_EMAIL        email da caixa que recebe o link de login
                                (default: igual ao MEU_PLUGGY_EMAIL)
  MEU_PLUGGY_IMAP_APP_PASSWORD "senha de app" do Gmail dessa caixa
                                (myaccount.google.com/apppasswords) —
                                NÃO é a senha normal da conta Google.

Uso (de dentro de backend/, com o venv ativado):
  py -m scripts.atualizar_meupluggy
"""
from __future__ import annotations

import datetime as dt
import email
import imaplib
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import Page, sync_playwright

# Garante que .env é carregado mesmo rodando este script isolado (mesmo
# padrão de app/database.py, pra não repetir o bug de "esqueceu load_dotenv").
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

LOGIN_TIMEOUT_SEGUNDOS = 90
ATUALIZACAO_TIMEOUT_SEGUNDOS = 60


def _env_obrigatoria(nome: str) -> str:
    valor = os.environ.get(nome)
    if not valor:
        sys.exit(
            f"Faltou configurar {nome} (variável de ambiente ou .env). "
            "Veja o cabeçalho deste arquivo pra saber quais credenciais são necessárias."
        )
    return valor


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
    # Emails em HTML costumam terminar o link com aspas/tags coladas.
    link = match.group(0).rstrip('"\'<>)')
    return link


def buscar_link_de_login(imap_email: str, imap_senha_app: str) -> str:
    """Faz polling na caixa de entrada via IMAP até achar o email do Auth0
    com o link de login. Marca como lido pra não reprocessar em execuções
    futuras."""
    prazo = time.time() + LOGIN_TIMEOUT_SEGUNDOS
    print(f"Esperando o email de login chegar em {imap_email}...")
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
    raise TimeoutError(
        "Não recebeu o email de login a tempo. Confira a caixa de entrada manualmente "
        "(pode ser que o Gmail tenha marcado como spam, ou o IMAP esteja desativado nas "
        "configurações da conta)."
    )


def _clicar_resiliente(page: Page, texto: str, timeout_ms: int = 15000) -> None:
    """`page.click()` puro às vezes trava esperando a ação "completar" quando
    tem uma animação/overlay (ex: cookie banner) por cima no instante do
    clique. Tenta um clique normal primeiro; se travar, cai pra
    `force=True` (ignora a checagem de "estável"/sobreposição)."""
    locator = page.get_by_text(texto, exact=True).first
    try:
        locator.click(timeout=timeout_ms)
    except Exception:
        print(f'  Clique normal em "{texto}" travou, tentando force=True.')
        locator.click(timeout=timeout_ms, force=True)


def logar(page: Page, meu_pluggy_email: str, imap_email: str, imap_senha_app: str) -> None:
    page.goto("https://meu.pluggy.ai/", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)
    _clicar_resiliente(page, "Entrar")
    page.wait_for_selector('input[type="email"]', timeout=15000)
    page.fill('input[type="email"]', meu_pluggy_email)
    _clicar_resiliente(page, "Enviar")
    page.wait_for_timeout(1500)  # dá tempo do Auth0 processar o envio

    link = buscar_link_de_login(imap_email, imap_senha_app)
    print("Link de login encontrado, autenticando...")
    page.goto(link, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)


def listar_links_de_conexoes(page: Page) -> list[str]:
    page.goto("https://meu.pluggy.ai/connections", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)
    hrefs = {
        a.get_attribute("href")
        for a in page.query_selector_all('a[href^="/connections/"]')
        if a.get_attribute("href") and a.get_attribute("href") != "/connections"
    }
    return sorted(hrefs)


def atualizar_conexao(page: Page, href: str) -> bool:
    url = f"https://meu.pluggy.ai{href}"
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)
    try:
        _clicar_resiliente(page, "Atualizar", timeout_ms=15000)
    except Exception as exc:
        print(f"  {url}: não consegui clicar em Atualizar ({exc})")
        return False

    try:
        page.wait_for_selector(
            "text=Atualizando a sua conta", state="hidden", timeout=ATUALIZACAO_TIMEOUT_SEGUNDOS * 1000
        )
    except Exception:
        print(f"  {url}: atualização demorou mais que {ATUALIZACAO_TIMEOUT_SEGUNDOS}s, seguindo mesmo assim.")
    return True


def sincronizar_nosso_backend() -> None:
    """Depois que o meu.pluggy.ai tem dado fresco, dispara nosso próprio
    sync direto no banco (mesma lógica do botão "Atualizar agora"), pra não
    esperar o job de 20 min."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app.database import SessionLocal
    from app.services import pluggy_sync

    db = SessionLocal()
    try:
        resultados = pluggy_sync.sync_all_items(db)
        for item_id, erro in resultados.items():
            print(f"  nosso sync — item {item_id}: {'ERRO: ' + str(erro) if erro else 'OK'}")
    finally:
        db.close()


def main() -> None:
    meu_pluggy_email = _env_obrigatoria("MEU_PLUGGY_EMAIL")
    imap_email = os.environ.get("MEU_PLUGGY_IMAP_EMAIL", meu_pluggy_email)
    imap_senha_app = _env_obrigatoria("MEU_PLUGGY_IMAP_APP_PASSWORD")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        logar(page, meu_pluggy_email, imap_email, imap_senha_app)

        links = listar_links_de_conexoes(page)
        print(f"{len(links)} conexão(ões) encontrada(s).")

        for href in links:
            ok = atualizar_conexao(page, href)
            print(f"  {href}: {'atualizado' if ok else 'FALHOU'}.")

        browser.close()

    print("Sincronizando nosso backend com os dados frescos...")
    sincronizar_nosso_backend()
    print("Concluído.")


if __name__ == "__main__":
    main()
