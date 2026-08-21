"""Envio de notificações por email via Gmail SMTP (App Password).

Variáveis de ambiente:
- SMTP_EMAIL: conta Gmail remetente.
- SMTP_APP_PASSWORD: App Password gerada em myaccount.google.com/apppasswords
  (nunca a senha normal da conta — Gmail exige 2FA ativado pra gerar).
- NOTIFY_EMAIL: destinatário das notificações (default: o próprio SMTP_EMAIL).
"""
import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _configurado() -> bool:
    return bool(os.getenv("SMTP_EMAIL") and os.getenv("SMTP_APP_PASSWORD"))


def send_email(subject: str, body: str, html: str | None = None) -> bool:
    """Manda um email de notificação. `body` é sempre o fallback texto puro
    (clientes de email antigos, preview de notificação); `html`, se
    passado, é a versão bonita (ver `render_email_html`) — a maioria dos
    clientes mostra o HTML quando os dois estão presentes. Retorna False
    (e só loga) se o SMTP não estiver configurado ou se o envio falhar —
    notificação nunca deve derrubar o fluxo principal (sync, criação de
    meta, etc)."""
    if not _configurado():
        logger.info("Email não enviado (SMTP não configurado): %s", subject)
        return False

    remetente = os.getenv("SMTP_EMAIL")
    senha_app = os.getenv("SMTP_APP_PASSWORD")
    # `or remetente` (não só o default do getenv) porque o .env.example
    # deixa NOTIFY_EMAIL="" (presente, vazio) — getenv só usa o default
    # quando a variável está AUSENTE, então com ela vazia isso mandaria
    # o email pra destinatário "" e falharia silenciosamente.
    destinatario = os.getenv("NOTIFY_EMAIL") or remetente

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = remetente
    msg["To"] = destinatario
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(remetente, senha_app)
            smtp.send_message(msg)
        return True
    except Exception:
        logger.exception("Falha ao enviar email: %s", subject)
        return False


# Paleta por tipo de alerta — cor de destaque no topo do email e no ícone.
_CORES = {
    "info": "#6c5ce7",
    "aviso": "#f39c12",
    "perigo": "#e74c3c",
    "sucesso": "#2ecc71",
}


def render_email_html(
    *, titulo: str, subtitulo: str, itens: list[tuple[str, str]], tipo: str = "info", rodape: str = ""
) -> str:
    """Monta um email transacional simples e responsivo (tabela + CSS
    inline, como exige a maioria dos clientes de email — nada de
    stylesheet externo ou flexbox/grid). `itens` é uma lista de
    (linha_principal, linha_secundária) — ex: ("Netflix", "R$ 39,90 · vence hoje").
    """
    cor = _CORES.get(tipo, _CORES["info"])
    linhas_html = "".join(
        f"""
        <tr>
          <td style="padding:14px 20px;border-bottom:1px solid #2a2a35;">
            <div style="font-size:14px;color:#e8e8f0;font-weight:600;">{principal}</div>
            <div style="font-size:13px;color:#9b9bab;margin-top:2px;">{secundaria}</div>
          </td>
        </tr>"""
        for principal, secundaria in itens
    )

    return f"""\
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background-color:#0d0d12;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#0d0d12;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="max-width:480px;width:100%;background-color:#16161d;border-radius:12px;overflow:hidden;border:1px solid #2a2a35;">
            <tr>
              <td style="background-color:{cor};padding:4px;"></td>
            </tr>
            <tr>
              <td style="padding:24px 20px 4px 20px;">
                <div style="font-size:12px;letter-spacing:0.5px;color:#9b9bab;text-transform:uppercase;font-weight:600;">Finanças</div>
                <div style="font-size:19px;color:#f2f2f7;font-weight:700;margin-top:6px;">{titulo}</div>
                <div style="font-size:14px;color:#b4b4c2;margin-top:4px;">{subtitulo}</div>
              </td>
            </tr>
            <tr>
              <td style="padding:12px 0 4px 0;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                  {linhas_html}
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:16px 20px 22px 20px;">
                <div style="font-size:12px;color:#6f6f80;">{rodape or "Enviado automaticamente pelo seu sistema de controle financeiro."}</div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""
