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


def send_email(subject: str, body: str) -> bool:
    """Manda um email de notificação. Retorna False (e só loga) se o SMTP
    não estiver configurado ou se o envio falhar — notificação nunca deve
    derrubar o fluxo principal (sync, criação de meta, etc)."""
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

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(remetente, senha_app)
            smtp.send_message(msg)
        return True
    except Exception:
        logger.exception("Falha ao enviar email: %s", subject)
        return False
